"""Resumo de trafego + ecommerce por canal — leitura, pro Julio responder
perguntas simples de trafego com dado real (nao interrogatorio).

Metricas escolhidas com base em referencia-analise-ecommerce.md: o minimo
que responde "como esta o trafego" sem afogar o LLM em campos irrelevantes
(o catalogo completo tem 375 dimensoes e 95 metricas — a esmagadora maioria
nao serve pra essa pergunta).
"""
import json

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from src import config

SCOPES = ["https://www.googleapis.com/auth/analytics.readonly"]

METRICAS = [
    "sessions", "engagedSessions", "engagementRate",
    "ecommercePurchases", "purchaseRevenue", "averagePurchaseRevenue",
]


def _data_service():
    creds = Credentials(token=None, scopes=SCOPES, **config.ga4_credentials_config())
    return build("analyticsdata", "v1beta", credentials=creds, cache_discovery=False)


def _linha(row: dict, com_canal: bool) -> dict:
    valores = {m: row["metricValues"][i]["value"] for i, m in enumerate(METRICAS)}
    resultado = {
        "sessoes": int(valores["sessions"]),
        "sessoes_engajadas": int(valores["engagedSessions"]),
        "taxa_engajamento": round(float(valores["engagementRate"]), 4),
        "compras": int(float(valores["ecommercePurchases"])),
        "receita_brl": round(float(valores["purchaseRevenue"]), 2),
        "ticket_medio_brl": round(float(valores["averagePurchaseRevenue"]), 2),
    }
    if com_canal:
        resultado["canal"] = row["dimensionValues"][0]["value"]
    return resultado


def resumo_trafego(dias: int = 7) -> dict:
    service = _data_service()
    property_path = config.ga4_property_path()
    periodo = {"startDate": f"{dias}daysAgo", "endDate": "today"}

    corpo_total = {"dateRanges": [periodo], "metrics": [{"name": m} for m in METRICAS]}
    resp_total = service.properties().runReport(property=property_path, body=corpo_total).execute()
    total = _linha(resp_total["rows"][0], com_canal=False) if resp_total.get("rows") else None

    corpo_canal = {
        "dateRanges": [periodo],
        "dimensions": [{"name": "sessionDefaultChannelGroup"}],
        "metrics": [{"name": m} for m in METRICAS],
        "orderBys": [{"metric": {"metricName": "sessions"}, "desc": True}],
    }
    resp_canal = service.properties().runReport(property=property_path, body=corpo_canal).execute()
    por_canal = [_linha(row, com_canal=True) for row in resp_canal.get("rows", [])]

    return {
        "property_path": property_path,
        "periodo_dias": dias,
        "total": total,
        "por_canal": por_canal,
    }


if __name__ == "__main__":
    print(json.dumps(resumo_trafego(), ensure_ascii=False, indent=2))
