"""Executa um runReport genérico na propriedade GA4 do site --
dimensões e métricas escolhidas pelo agente (consultadas antes via
ga4_consultar_schema), não uma análise pré-definida. Substitui a
necessidade de uma tool nova por combinação de dado que alguém
antecipasse.

Uso:
    echo '{"dimensoes": [...], "metricas": [...], "dias": 7}' | python report.py <site>
"""
import json
import sys
from pathlib import Path

from dotenv import dotenv_values
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

REPO_ROOT = Path(__file__).resolve().parents[3]
SCOPES = ["https://www.googleapis.com/auth/analytics.readonly"]


def _service_e_property(site: str):
    comum = dotenv_values(REPO_ROOT / ".env")
    do_site = dotenv_values(REPO_ROOT / "SITES" / site / ".env")
    if "GA4_PROPERTY_ID" not in do_site:
        return None, None
    creds = Credentials(
        token=None, scopes=SCOPES,
        client_id=comum["GA4_CLIENT_ID"], client_secret=comum["GA4_CLIENT_SECRET"],
        refresh_token=comum["GA4_REFRESH_TOKEN"], token_uri="https://oauth2.googleapis.com/token",
    )
    service = build("analyticsdata", "v1beta", credentials=creds, cache_discovery=False)
    return service, f"properties/{do_site['GA4_PROPERTY_ID']}"


def _formatar_linhas(resposta: dict, dimensoes: list[str], metricas: list[str]) -> list[dict]:
    linhas = []
    for linha in resposta.get("rows", []):
        registro = {}
        for nome, valor in zip(dimensoes, linha.get("dimensionValues", [])):
            registro[nome] = valor.get("value")
        for nome, valor in zip(metricas, linha.get("metricValues", [])):
            registro[nome] = valor.get("value")
        linhas.append(registro)
    return linhas


def executar_report(site: str, dimensoes: list[str], metricas: list[str], dias: int = 7) -> dict:
    service, property_path = _service_e_property(site)
    if service is None:
        return {"ok": False, "erros": [f"site '{site}' sem GA4_PROPERTY_ID configurado"]}

    corpo = {
        "dimensions": [{"name": d} for d in dimensoes],
        "metrics": [{"name": m} for m in metricas],
        "dateRanges": [{"startDate": f"{dias}daysAgo", "endDate": "today"}],
    }
    try:
        resposta = service.properties().runReport(property=property_path, body=corpo).execute()
    except Exception as exc:  # noqa: BLE001 -- erro real da API, formato variavel
        return {"ok": False, "erros": [str(exc)]}

    return {
        "ok": True,
        "site": site, "periodo_dias": dias,
        "linhas": _formatar_linhas(resposta, dimensoes, metricas),
    }


if __name__ == "__main__":
    site_arg = sys.argv[1] if len(sys.argv) > 1 else "3gfoods"
    entrada = json.load(sys.stdin)
    print(json.dumps(
        executar_report(site_arg, entrada["dimensoes"], entrada["metricas"], entrada.get("dias", 7)),
        ensure_ascii=False, indent=2,
    ))
