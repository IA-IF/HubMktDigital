"""Fase B do esquema de analise de vendas (Ads + GA4) -- ver
docs/superpowers/specs/2026-07-22-esquema-analise-vendas-design.md.

Uso:
    python analise_ads.py [site] [dias]
    python analise_ads.py 3gfoods 7

Credenciais so da raiz do projeto (.env + SITES/<site>/.env), nunca de
LEGADO/.
"""
import json
import sys
from pathlib import Path

from dotenv import dotenv_values
from google.ads.googleads.client import GoogleAdsClient

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "GA4" / "analise_vendas"))

from eficiencia import calcular_eficiencia_ads  # noqa: E402
from analise_vendas import rodar_analise as rodar_analise_ga4  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]


def _cliente_ads(site: str):
    comum = dotenv_values(REPO_ROOT / ".env")
    do_site = dotenv_values(REPO_ROOT / "SITES" / site / ".env")
    if "GOOGLE_ADS_CUSTOMER_ID" not in do_site:
        raise SystemExit(
            f"Site '{site}' nao tem GOOGLE_ADS_CUSTOMER_ID configurado — confirme "
            f"que SITES/{site}/.env existe e tem essa variavel."
        )
    cfg = {
        "developer_token": comum["GOOGLE_ADS_DEVELOPER_TOKEN"],
        "client_id": comum["GOOGLE_ADS_CLIENT_ID"],
        "client_secret": comum["GOOGLE_ADS_CLIENT_SECRET"],
        "refresh_token": comum["GOOGLE_ADS_REFRESH_TOKEN"],
        "login_customer_id": comum["GOOGLE_ADS_LOGIN_CUSTOMER_ID"],
        "use_proto_plus": True,
    }
    client = GoogleAdsClient.load_from_dict(cfg)
    cid = do_site["GOOGLE_ADS_CUSTOMER_ID"].replace("-", "")
    return client, cid


# So compra de verdade -- ROAS/CPA/CAC medem eficiencia de VENDA, nao de
# etapa de funil (add_to_cart/begin_checkout tem "valor" no Ads mas nao e
# receita real, e contar eles infla o numero pra muito acima do real).
EVENTOS_DE_VENDA = ("purchase", "compra")


def buscar_dados_ads(client, cid: str, dias: int) -> dict:
    """metrics.conversions/.conversions_value sem filtro somam TODAS as
    conversion actions da conta, incluindo eventos nao-comerciais
    diluindo o numero (achado real: 3G Foods tem page_view/session_start/
    etc marcados como conversao, ver TOOLS/ADWORDS/... e pratico.md). Por
    isso a query aqui segmenta por conversion_action_name e so soma as
    que batem com evento de negocio real -- mesmo criterio ja usado em
    LEGADO/agente-ads/src/conversion_actions.py (nao importado, so mesmo
    criterio replicado aqui pra nao depender de LEGADO)."""
    service = client.get_service("GoogleAdsService")

    query_custo = f"""
        SELECT metrics.cost_micros, metrics.clicks, metrics.impressions,
               metrics.search_impression_share
        FROM campaign
        WHERE segments.date DURING LAST_{dias}_DAYS
          AND campaign.status != 'REMOVED'
    """
    cost = clicks = impressions = 0
    shares = []
    for row in service.search(customer_id=cid, query=query_custo):
        m = row.metrics
        cost += m.cost_micros
        clicks += m.clicks
        impressions += m.impressions
        if m.search_impression_share > 0:
            shares.append(m.search_impression_share)

    query_conversoes = f"""
        SELECT segments.conversion_action_name, metrics.conversions,
               metrics.conversions_value
        FROM campaign
        WHERE segments.date DURING LAST_{dias}_DAYS
          AND campaign.status != 'REMOVED'
          AND metrics.conversions > 0
    """
    conversions = conversions_value = 0.0
    for row in service.search(customer_id=cid, query=query_conversoes):
        nome = row.segments.conversion_action_name.lower()
        if any(s in nome for s in EVENTOS_DE_VENDA):
            conversions += row.metrics.conversions
            conversions_value += row.metrics.conversions_value

    return {
        "cost": cost / 1_000_000,
        "clicks": clicks,
        "impressions": impressions,
        "conversions": conversions,
        "conversions_value": conversions_value,
        "impression_share": round(sum(shares) / len(shares), 4) if shares else None,
    }


def rodar_analise_ads(site: str, dias: int = 7) -> dict:
    client, cid = _cliente_ads(site)
    dados_ads = buscar_dados_ads(client, cid, dias)

    dados_ga4 = rodar_analise_ga4(site, dias)
    ga4_compras_total = sum(c["compras"] for c in dados_ga4["canais"])

    return {
        "site": site,
        "periodo_dias": dias,
        "eficiencia_ads": calcular_eficiencia_ads({**dados_ads, "ga4_compras_total": ga4_compras_total}),
        "ga4_compras_total_todos_canais": ga4_compras_total,
    }


if __name__ == "__main__":
    site_arg = sys.argv[1] if len(sys.argv) > 1 else "3gfoods"
    dias_arg = int(sys.argv[2]) if len(sys.argv) > 2 else 7
    print(json.dumps(rodar_analise_ads(site_arg, dias_arg), ensure_ascii=False, indent=2))
