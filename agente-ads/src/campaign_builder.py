"""Cria campanhas novas no Google Ads a partir de uma proposta confirmada por humano.

Usado pelo telegram_bot.py: o responsavel de marketing conversa com o agente,
que monta uma proposta estruturada e so chama `criar_campanha` depois de
confirmacao explicita ("sim") no chat.

Seguranca: a campanha sempre nasce com status PAUSADA — mesmo apos a
confirmacao no chat, alguem precisa entrar no Google Ads e ativa-la
manualmente antes de gastar dinheiro de verdade.
"""
from google.ads.googleads.client import GoogleAdsClient

from src import config

GEO_TARGET_BRASIL = "geoTargetConstants/2076"
LANGUAGE_PORTUGUES = "languageConstants/1014"


def _criar_orcamento(client: GoogleAdsClient, cid: str, nome: str, valor_diario_brl: float) -> str:
    service = client.get_service("CampaignBudgetService")
    op = client.get_type("CampaignBudgetOperation")
    budget = op.create
    budget.name = f"{nome} — orcamento"
    budget.amount_micros = int(valor_diario_brl * 1_000_000)
    budget.delivery_method = client.enums.BudgetDeliveryMethodEnum.STANDARD
    resposta = service.mutate_campaign_budgets(customer_id=cid, operations=[op])
    return resposta.results[0].resource_name


def _criar_campanha(client: GoogleAdsClient, cid: str, nome: str, budget_resource: str) -> str:
    service = client.get_service("CampaignService")
    op = client.get_type("CampaignOperation")
    campanha = op.create
    campanha.name = nome
    campanha.status = client.enums.CampaignStatusEnum.PAUSED
    campanha.advertising_channel_type = client.enums.AdvertisingChannelTypeEnum.SEARCH
    campanha.campaign_budget = budget_resource
    campanha.manual_cpc.enhanced_cpc_enabled = False
    campanha.network_settings.target_google_search = True
    campanha.network_settings.target_search_network = False
    campanha.network_settings.target_content_network = False
    resposta = service.mutate_campaigns(customer_id=cid, operations=[op])
    return resposta.results[0].resource_name


def _criar_targeting(client: GoogleAdsClient, cid: str, campanha_resource: str) -> None:
    service = client.get_service("CampaignCriterionService")

    op_geo = client.get_type("CampaignCriterionOperation")
    op_geo.create.campaign = campanha_resource
    op_geo.create.location.geo_target_constant = GEO_TARGET_BRASIL

    op_idioma = client.get_type("CampaignCriterionOperation")
    op_idioma.create.campaign = campanha_resource
    op_idioma.create.language.language_constant = LANGUAGE_PORTUGUES

    service.mutate_campaign_criteria(customer_id=cid, operations=[op_geo, op_idioma])


def _criar_grupo_anuncio(client: GoogleAdsClient, cid: str, campanha_resource: str,
                          nome: str, lance_inicial_brl: float) -> str:
    service = client.get_service("AdGroupService")
    op = client.get_type("AdGroupOperation")
    grupo = op.create
    grupo.name = nome
    grupo.campaign = campanha_resource
    grupo.status = client.enums.AdGroupStatusEnum.ENABLED
    grupo.type_ = client.enums.AdGroupTypeEnum.SEARCH_STANDARD
    grupo.cpc_bid_micros = int(lance_inicial_brl * 1_000_000)
    resposta = service.mutate_ad_groups(customer_id=cid, operations=[op])
    return resposta.results[0].resource_name


def _criar_keywords(client: GoogleAdsClient, cid: str, grupo_resource: str,
                     palavras_chave: list[dict]) -> None:
    service = client.get_service("AdGroupCriterionService")
    tipos = client.enums.KeywordMatchTypeEnum
    operacoes = []
    for kw in palavras_chave:
        op = client.get_type("AdGroupCriterionOperation")
        op.create.ad_group = grupo_resource
        op.create.status = client.enums.AdGroupCriterionStatusEnum.ENABLED
        op.create.keyword.text = kw["texto"]
        op.create.keyword.match_type = getattr(tipos, kw.get("tipo_correspondencia", "BROAD"))
        operacoes.append(op)
    service.mutate_ad_group_criteria(customer_id=cid, operations=operacoes)


def _criar_anuncio(client: GoogleAdsClient, cid: str, grupo_resource: str,
                    titulos: list[str], descricoes: list[str], url_final: str) -> None:
    service = client.get_service("AdGroupAdService")
    op = client.get_type("AdGroupAdOperation")
    anuncio_ad_group = op.create
    anuncio_ad_group.ad_group = grupo_resource
    anuncio_ad_group.status = client.enums.AdGroupAdStatusEnum.ENABLED
    ad = anuncio_ad_group.ad
    ad.final_urls.append(url_final)
    for titulo in titulos:
        headline = client.get_type("AdTextAsset")
        headline.text = titulo
        ad.responsive_search_ad.headlines.append(headline)
    for descricao in descricoes:
        desc = client.get_type("AdTextAsset")
        desc.text = descricao
        ad.responsive_search_ad.descriptions.append(desc)
    service.mutate_ad_group_ads(customer_id=cid, operations=[op])


def criar_campanha(proposta: dict) -> dict:
    """Cria a campanha completa (orcamento, campanha, targeting, grupo, keywords, anuncio).

    `proposta` segue o schema TOOL_PROPOR_CAMPANHA de telegram_bot.py. Retorna
    um dict com os identificadores criados, para exibir ao usuario.

    Levanta excecao se qualquer etapa falhar — o que ja foi criado ate ali
    permanece no Google Ads (PAUSADO) e deve ser revisado/removido manualmente
    se necessario.
    """
    client = GoogleAdsClient.load_from_dict(config.google_ads_config())
    cid = config.customer_id()
    nome = proposta["nome_campanha"]

    budget_resource = _criar_orcamento(client, cid, nome, proposta["orcamento_diario_brl"])
    campanha_resource = _criar_campanha(client, cid, nome, budget_resource)
    _criar_targeting(client, cid, campanha_resource)
    grupo_resource = _criar_grupo_anuncio(
        client, cid, campanha_resource, f"{nome} — grupo 1", proposta["lance_inicial_brl"]
    )
    _criar_keywords(client, cid, grupo_resource, proposta["palavras_chave"])
    _criar_anuncio(
        client, cid, grupo_resource,
        proposta["titulos"], proposta["descricoes"], proposta["url_final"],
    )

    return {
        "campanha_resource": campanha_resource,
        "grupo_resource": grupo_resource,
        "status": "PAUSADA — ative manualmente no Google Ads apos revisar",
    }
