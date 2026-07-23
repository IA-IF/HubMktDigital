"""Fase B do esquema de analise de vendas: eficiencia do pago (Ads) +
CAC blended vs CAC so-Ads (cruza GA4). Ver
docs/superpowers/specs/2026-07-22-esquema-analise-vendas-design.md.

Calculo puro -- recebe dado ja buscado (Ads GAQL + total de compras real
do GA4, ver TOOLS/GA4/analise_vendas), devolve os numeros.
"""


def calcular_eficiencia_ads(dados: dict) -> dict:
    cost = dados["cost"]
    clicks = dados["clicks"]
    impressions = dados["impressions"]
    conversions = dados["conversions"]
    conversions_value = dados["conversions_value"]
    ga4_compras_total = dados["ga4_compras_total"]

    return {
        "roas": round(conversions_value / cost, 4) if cost else None,
        "cpa": round(cost / conversions, 2) if conversions else None,
        "ctr": round(clicks / impressions, 4) if impressions else None,
        "impression_share": dados.get("impression_share"),
        "cac_ads": round(cost / conversions, 2) if conversions else None,
        "cac_blended": round(cost / ga4_compras_total, 2) if ga4_compras_total else None,
    }
