"""Auditoria dinamica: abre o site de verdade (Playwright headless) e
confirma que o tracking funciona na pratica, nao so na configuracao.

Diferente do gtm_auditor.py (le a CONFIGURACAO do container via API — tags,
triggers, se ha mudanca nao publicada), este modulo confirma o
COMPORTAMENTO real em producao: o container certo carrega na pagina? o
dataLayer e populado com os eventos esperados? o hit realmente sai e chega
no Google? Sao complementares — um site pode passar 100% na auditoria
estatica (tudo configurado certo) e mesmo assim nao disparar nada de
verdade (ex: erro de JS impedindo o gtag de carregar, dataLayer nunca
populado). So a auditoria dinamica pega esse tipo de falha.

Decisao registrada no brainstorm.md (secao 2.1) resolvida aqui.
"""
import json
from datetime import date

from playwright.sync_api import sync_playwright

from src import config
from src import gtm_auditor

TIMEOUT_MS = 30_000
# "networkidle" sozinho da falso negativo: sites com mais scripts de
# terceiros (ex: 3G Foods, com Merchant Center + varias tags de Ads) ainda
# disparam GTM/GA4/conversao alguns segundos DEPOIS do idle. Confirmado
# empiricamente em 22/07/2026 — sem essa espera extra, o achado
# "gtm_carregou_container_esperado: false" foi falso alarme.
ESPERA_EXTRA_MS = 8_000


def _capturar(url: str) -> dict:
    requisicoes: list[str] = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.on("request", lambda req: requisicoes.append(req.url))
        page.goto(url, wait_until="networkidle", timeout=TIMEOUT_MS)
        page.wait_for_timeout(ESPERA_EXTRA_MS)
        data_layer = page.evaluate("() => window.dataLayer || []")
        browser.close()
    return {"data_layer": data_layer, "requisicoes": requisicoes}


def _eventos(data_layer: list) -> list[str]:
    return [item.get("event") for item in data_layer if isinstance(item, dict) and item.get("event")]


def _quantidade_suspeita(data_layer: list) -> bool:
    """True se TODO item de TODO evento de ecommerce tem a mesma quantidade
    fixa (ex: sempre 100) — indicio de valor placeholder, nao real (achado
    real ao auditar Integra Foods em 22/07/2026)."""
    quantidades = set()
    for item in data_layer:
        if not isinstance(item, dict):
            continue
        produtos = (item.get("ecommerce") or {}).get("items") or item.get("items") or []
        for produto in produtos:
            if "quantity" in produto:
                quantidades.add(produto["quantity"])
    return len(quantidades) == 1


def _gtm_carregou(requisicoes: list[str], public_id: str) -> bool:
    return any(f"gtm.js?id={public_id}" in r for r in requisicoes)


def _ga4_hit_disparou(requisicoes: list[str], measurement_id: str) -> bool:
    return any(
        "analytics.google.com/g/collect" in r and f"tid={measurement_id}" in r
        for r in requisicoes
    )


def auditar() -> dict:
    url = config.site_url()
    measurement_id_esperado = config.ga4_measurement_id()

    # Reaproveita a chamada de API do gtm_auditor pra saber o publicId
    # (GTM-XXXXXXX) do container que o .env aponta — e contra isso que
    # confere se o site carrega o container certo, nao qualquer GTM.
    service = gtm_auditor._service()
    container = service.accounts().containers().get(
        path=config.gtm_container_path()
    ).execute()
    public_id_esperado = container.get("publicId")

    captura = _capturar(url)
    data_layer = captura["data_layer"]
    requisicoes = captura["requisicoes"]

    eventos = _eventos(data_layer)
    gtm_ok = _gtm_carregou(requisicoes, public_id_esperado)
    ga4_ok = _ga4_hit_disparou(requisicoes, measurement_id_esperado)

    resultado = {
        "data_auditoria": date.today().isoformat(),
        "url": url,
        "container_esperado": public_id_esperado,
        "measurement_id_esperado": measurement_id_esperado,
        "resumo": {
            "eventos_no_dataLayer": eventos,
            "total_itens_dataLayer": len(data_layer),
            "total_requisicoes": len(requisicoes),
        },
        "achados": {
            "gtm_carregou_container_esperado": gtm_ok,
            "ga4_hit_disparou_com_measurement_id_esperado": ga4_ok,
            "dataLayer_vazio": len(data_layer) == 0,
            "quantidade_suspeita_fixa_no_ecommerce": _quantidade_suspeita(data_layer),
        },
    }

    caminho = config.DATA_DIR / f"gtm_dinamico_{resultado['data_auditoria']}.json"
    caminho.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
    return resultado


if __name__ == "__main__":
    resultado = auditar()
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
