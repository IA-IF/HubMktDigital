"""Auditoria de saude da propriedade GA4 — sempre leitura, nunca altera nada.

Ve ../gtm-workflow.md (pasta HubMktDigital) para o desenho do workflow (o
mesmo padrao vale aqui: resolver o site -> consultar a API -> reportar
achados, sem executar acao nenhuma). Cobre dois pontos:

- Admin API: quais eventos estao marcados como conversao (chave para o
  Ads importar certo e para o analyst.py do agente-cmo nao sugerir pausar
  campanha por "falta de conversao" quando o problema e tracking).
- Data API: contagem de eventos-chave do funil de ecommerce nos ultimos
  7 dias, pra confirmar que o tracking esta realmente registrando.
"""
import json
from datetime import date

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from src import config

SCOPES = ["https://www.googleapis.com/auth/analytics.readonly"]

EVENTOS_FUNIL = ["page_view", "view_item", "add_to_cart", "begin_checkout", "purchase"]


def _admin_service():
    creds = Credentials(token=None, scopes=SCOPES, **config.ga4_credentials_config())
    return build("analyticsadmin", "v1beta", credentials=creds, cache_discovery=False)


def _data_service():
    creds = Credentials(token=None, scopes=SCOPES, **config.ga4_credentials_config())
    return build("analyticsdata", "v1beta", credentials=creds, cache_discovery=False)


def _eventos_conversao(property_path: str) -> list[str]:
    service = _admin_service()
    resposta = service.properties().conversionEvents().list(parent=property_path).execute()
    return [e["eventName"] for e in resposta.get("conversionEvents", [])]


def _contagem_eventos_funil(property_path: str) -> dict:
    service = _data_service()
    body = {
        "dateRanges": [{"startDate": "7daysAgo", "endDate": "today"}],
        "dimensions": [{"name": "eventName"}],
        "metrics": [{"name": "eventCount"}],
    }
    resposta = service.properties().runReport(property=property_path, body=body).execute()

    contagens = {
        row["dimensionValues"][0]["value"]: int(row["metricValues"][0]["value"])
        for row in resposta.get("rows", [])
    }
    return {evento: contagens.get(evento, 0) for evento in EVENTOS_FUNIL}


def auditar() -> dict:
    property_path = config.ga4_property_path()

    eventos_conversao = _eventos_conversao(property_path)
    contagem_funil = _contagem_eventos_funil(property_path)

    resultado = {
        "data_auditoria": date.today().isoformat(),
        "property_path": property_path,
        "measurement_id_esperado": config.ga4_measurement_id(),
        "eventos_marcados_como_conversao": eventos_conversao,
        "contagem_funil_ultimos_7_dias": contagem_funil,
        "achados": {
            "purchase_marcado_como_conversao": "purchase" in eventos_conversao,
            "funil_sem_dados": [
                evento for evento, qtd in contagem_funil.items() if qtd == 0
            ],
        },
    }

    caminho = config.DATA_DIR / f"ga4_auditoria_{resultado['data_auditoria']}.json"
    caminho.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
    return resultado


if __name__ == "__main__":
    resultado = auditar()
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
