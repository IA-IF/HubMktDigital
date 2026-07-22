"""Auditoria de saude do Search Console — sempre leitura, nunca altera nada.

Ve ../gtm-workflow.md (pasta HubMktDigital) para o desenho do workflow (mesmo
padrao: resolver o site -> consultar a API -> reportar achados). Diferente
de GTM/GA4, o Search Console e 100% diagnostico — nao existe acao executavel
aqui, so alertas/sugestoes (ver brainstorm.md, secao 3.3).
"""
import json
from datetime import date, timedelta

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from src import config

SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]


def _service():
    creds = Credentials(token=None, scopes=SCOPES, **config.sc_credentials_config())
    return build("searchconsole", "v1", credentials=creds, cache_discovery=False)


def _status_sitemaps(service, site_url: str) -> list[dict]:
    resposta = service.sitemaps().list(siteUrl=site_url).execute()
    return [
        {
            "path": s.get("path"),
            "tipo": s.get("type"),
            "ultima_leitura": s.get("lastDownloaded"),
            "paginas_encontradas": s.get("contents", [{}])[0].get("submitted") if s.get("contents") else None,
            "erros": int(s.get("errors", 0)),
            "avisos": int(s.get("warnings", 0)),
        }
        for s in resposta.get("sitemap", [])
    ]


def _desempenho_28_dias(service, site_url: str) -> dict:
    fim = date.today() - timedelta(days=3)  # dados do SC tem atraso de ~2-3 dias
    inicio = fim - timedelta(days=28)
    body = {
        "startDate": inicio.isoformat(),
        "endDate": fim.isoformat(),
        "dimensions": ["query"],
        "rowLimit": 10,
    }
    resposta = service.searchanalytics().query(siteUrl=site_url, body=body).execute()
    linhas = resposta.get("rows", [])
    return {
        "periodo": f"{inicio.isoformat()} a {fim.isoformat()}",
        "top_queries": [
            {
                "query": row["keys"][0],
                "cliques": row["clicks"],
                "impressoes": row["impressions"],
                "ctr": round(row["ctr"], 4),
                "posicao_media": round(row["position"], 1),
            }
            for row in linhas
        ],
        "sem_dados_no_periodo": len(linhas) == 0,
    }


def auditar() -> dict:
    service = _service()
    site_url = config.sc_site_url()

    sitemaps = _status_sitemaps(service, site_url)
    desempenho = _desempenho_28_dias(service, site_url)

    resultado = {
        "data_auditoria": date.today().isoformat(),
        "site_url": site_url,
        "sitemaps": sitemaps,
        "desempenho": desempenho,
        "achados": {
            "sitemaps_com_erro": [s["path"] for s in sitemaps if s["erros"]],
            "sem_trafego_organico_recente": desempenho["sem_dados_no_periodo"],
        },
    }

    caminho = config.DATA_DIR / f"search_console_auditoria_{resultado['data_auditoria']}.json"
    caminho.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
    return resultado


if __name__ == "__main__":
    resultado = auditar()
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
