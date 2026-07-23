"""Busca o dado bruto real do GA4 pra alimentar funil.py/canais.py/
ecommerce_taxas.py. Unica peca deste modulo que fala com a API de
verdade -- ver Task 4 do plano, sem teste automatizado (a logica de
calculo ja foi testada nas pecas puras).
"""
from funil import ETAPAS_FUNIL


def buscar_contagens_funil(service, property_path: str, dias: int) -> dict[str, int]:
    corpo = {
        "dateRanges": [{"startDate": f"{dias}daysAgo", "endDate": "today"}],
        "dimensions": [{"name": "eventName"}],
        "metrics": [{"name": "eventCount"}],
        "dimensionFilter": {
            "filter": {
                "fieldName": "eventName",
                "inListFilter": {"values": ETAPAS_FUNIL},
            }
        },
    }
    resp = service.properties().runReport(property=property_path, body=corpo).execute()
    contagens = {}
    for row in resp.get("rows", []):
        nome_evento = row["dimensionValues"][0]["value"]
        contagem = int(row["metricValues"][0]["value"])
        contagens[nome_evento] = contagem
    return contagens


def buscar_linhas_canal(service, property_path: str, dias: int) -> list[dict]:
    corpo = {
        "dateRanges": [{"startDate": f"{dias}daysAgo", "endDate": "today"}],
        "dimensions": [{"name": "sessionDefaultChannelGroup"}],
        "metrics": [{"name": "sessions"}, {"name": "ecommercePurchases"}],
    }
    resp = service.properties().runReport(property=property_path, body=corpo).execute()
    linhas = []
    for row in resp.get("rows", []):
        linhas.append({
            "canal": row["dimensionValues"][0]["value"],
            "sessoes": int(row["metricValues"][0]["value"]),
            "compras": int(float(row["metricValues"][1]["value"])),
        })
    return linhas


def buscar_dados_ecommerce(service, property_path: str, dias: int) -> dict:
    metricas = ["itemsViewed", "addToCarts", "checkouts", "ecommercePurchases",
                "purchaseRevenue", "transactions"]
    corpo = {
        "dateRanges": [{"startDate": f"{dias}daysAgo", "endDate": "today"}],
        "metrics": [{"name": m} for m in metricas],
    }
    resp = service.properties().runReport(property=property_path, body=corpo).execute()
    if not resp.get("rows"):
        return {"items_viewed": 0, "add_to_carts": 0, "checkouts": 0,
                "ecommerce_purchases": 0, "purchase_revenue": 0.0, "transactions": 0}
    valores = resp["rows"][0]["metricValues"]
    return {
        "items_viewed": int(valores[0]["value"]),
        "add_to_carts": int(valores[1]["value"]),
        "checkouts": int(valores[2]["value"]),
        "ecommerce_purchases": int(float(valores[3]["value"])),
        "purchase_revenue": float(valores[4]["value"]),
        "transactions": int(float(valores[5]["value"])),
    }
