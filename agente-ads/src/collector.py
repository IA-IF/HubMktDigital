"""Coleta métricas do Google Ads via GAQL (Prompt 2 do guia).

Busca, dos últimos 30 dias: gasto, impressões, cliques, CTR, conversões,
valor de conversão e ROAS por campanha, grupo de anúncios e palavra-chave.
Salva o resultado em data/coleta_YYYY-MM-DD.json.
"""
import json
from datetime import date

from google.ads.googleads.client import GoogleAdsClient

from src import config

METRICAS = (
    "metrics.cost_micros, metrics.impressions, metrics.clicks, metrics.ctr, "
    "metrics.conversions, metrics.conversions_value"
)

QUERY_CAMPANHAS = f"""
    SELECT campaign.id, campaign.name, campaign.status,
           campaign_budget.amount_micros, {METRICAS}
    FROM campaign
    WHERE segments.date DURING LAST_30_DAYS
      AND campaign.status != 'REMOVED'
"""

QUERY_GRUPOS = f"""
    SELECT campaign.id, campaign.name, ad_group.id, ad_group.name,
           ad_group.status, {METRICAS}
    FROM ad_group
    WHERE segments.date DURING LAST_30_DAYS
      AND ad_group.status != 'REMOVED'
"""

QUERY_KEYWORDS = f"""
    SELECT campaign.id, campaign.name, ad_group.id, ad_group.name,
           ad_group_criterion.criterion_id, ad_group_criterion.keyword.text,
           ad_group_criterion.keyword.match_type, ad_group_criterion.status,
           ad_group_criterion.effective_cpc_bid_micros, {METRICAS}
    FROM keyword_view
    WHERE segments.date DURING LAST_30_DAYS
      AND ad_group_criterion.status != 'REMOVED'
"""


def _metricas(row) -> dict:
    gasto = row.metrics.cost_micros / 1_000_000
    valor_conv = row.metrics.conversions_value
    return {
        "gasto_brl": round(gasto, 2),
        "impressoes": row.metrics.impressions,
        "cliques": row.metrics.clicks,
        "ctr": round(row.metrics.ctr, 4),
        "conversoes": round(row.metrics.conversions, 2),
        "valor_conversao_brl": round(valor_conv, 2),
        "roas": round(valor_conv / gasto, 2) if gasto > 0 else None,
    }


def coletar() -> dict:
    client = GoogleAdsClient.load_from_dict(config.google_ads_config())
    service = client.get_service("GoogleAdsService")
    cid = config.customer_id()

    dados = {"data_coleta": date.today().isoformat(), "periodo": "LAST_30_DAYS",
             "campanhas": [], "grupos_anuncio": [], "keywords": []}

    for batch in service.search_stream(customer_id=cid, query=QUERY_CAMPANHAS):
        for row in batch.results:
            dados["campanhas"].append({
                "campanha_id": row.campaign.id,
                "campanha": row.campaign.name,
                "status": row.campaign.status.name,
                "orcamento_diario_brl": round(row.campaign_budget.amount_micros / 1_000_000, 2),
                **_metricas(row),
            })

    for batch in service.search_stream(customer_id=cid, query=QUERY_GRUPOS):
        for row in batch.results:
            dados["grupos_anuncio"].append({
                "campanha_id": row.campaign.id,
                "campanha": row.campaign.name,
                "grupo_id": row.ad_group.id,
                "grupo": row.ad_group.name,
                "status": row.ad_group.status.name,
                **_metricas(row),
            })

    for batch in service.search_stream(customer_id=cid, query=QUERY_KEYWORDS):
        for row in batch.results:
            crit = row.ad_group_criterion
            dados["keywords"].append({
                "campanha_id": row.campaign.id,
                "campanha": row.campaign.name,
                "grupo_id": row.ad_group.id,
                "grupo": row.ad_group.name,
                "criterio_id": crit.criterion_id,
                "keyword": crit.keyword.text,
                "match_type": crit.keyword.match_type.name,
                "status": crit.status.name,
                "cpc_max_brl": round(crit.effective_cpc_bid_micros / 1_000_000, 2),
                **_metricas(row),
            })

    return dados


def coletar_e_salvar() -> tuple[dict, str]:
    dados = coletar()
    caminho = config.DATA_DIR / f"coleta_{dados['data_coleta']}.json"
    caminho.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
    return dados, str(caminho)


if __name__ == "__main__":
    dados, caminho = coletar_e_salvar()
    print(f"Coleta salva em {caminho}: {len(dados['campanhas'])} campanhas, "
          f"{len(dados['grupos_anuncio'])} grupos, {len(dados['keywords'])} keywords")
