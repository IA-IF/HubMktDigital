"""Fala com a API de verdade (mutate) -- unica peca deste modulo sem
teste automatizado, mesma logica de coleta.py nas outras tools (a
validacao ja foi testada em validacao.py). Site explicito por chamada,
sem estado global via env SITE.

Guardrail inegociavel: a campanha sempre nasce PAUSADA -- ativar e
decisao manual de quem revisa no Google Ads, nunca automatica.
"""
from google.ads.googleads.client import GoogleAdsClient

from validacao import brl_para_micros

GEO_TARGET_BRASIL = "geoTargetConstants/2076"
LANGUAGE_PORTUGUES = "languageConstants/1014"


def _criar_orcamento(client: GoogleAdsClient, cid: str, nome: str, valor_diario_brl: float) -> str:
    service = client.get_service("CampaignBudgetService")
    op = client.get_type("CampaignBudgetOperation")
    budget = op.create
    budget.name = f"{nome} — orcamento"
    budget.amount_micros = brl_para_micros(valor_diario_brl)
    budget.delivery_method = client.enums.BudgetDeliveryMethodEnum.STANDARD
    # explicitly_shared default e True (orcamento pra compartilhar entre
    # campanhas) -- cada chamada aqui cria 1 orcamento dedicado pra 1
    # campanha so, e Smart Bidding no nivel da campanha exige orcamento
    # NAO compartilhado (senao a API rejeita com
    # BIDDING_STRATEGY_TYPE_INCOMPATIBLE_WITH_SHARED_BUDGET).
    budget.explicitly_shared = False
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
    # Obrigatorio desde a v24 da API (autodeclaracao de publicidade politica UE) --
    # nenhum dos nossos sites e advertiser politico.
    campanha.contains_eu_political_advertising = (
        client.enums.EuPoliticalAdvertisingStatusEnum.DOES_NOT_CONTAIN_EU_POLITICAL_ADVERTISING
    )
    # Smart Bidding orientado a conversao -- sem historico de conversao
    # ainda, entao sem target_cpa/bid ceiling (deixa o algoritmo aprender
    # livre dentro do orcamento). Objetivo do projeto e campanha que gere
    # conversao de verdade (ver ARQUITETURA/entendimento.md); manual_cpc
    # (bidding anterior) nao otimiza pra conversao nenhuma.
    campanha.maximize_conversions = {}
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


def _criar_grupo_anuncio(client: GoogleAdsClient, cid: str, campanha_resource: str, nome: str) -> str:
    """Sem cpc_bid_micros -- bid manual por grupo de anuncio nao se
    aplica com a campanha em Smart Bidding (maximize_conversions),
    quem decide o lance e o algoritmo da API."""
    service = client.get_service("AdGroupService")
    op = client.get_type("AdGroupOperation")
    grupo = op.create
    grupo.name = nome
    grupo.campaign = campanha_resource
    grupo.status = client.enums.AdGroupStatusEnum.ENABLED
    grupo.type_ = client.enums.AdGroupTypeEnum.SEARCH_STANDARD
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


def executar_criacao(client: GoogleAdsClient, cid: str, proposta: dict) -> dict:
    """Assume que `proposta` ja passou por validacao.validar_proposta.
    Levanta excecao se qualquer etapa falhar -- o que ja foi criado ate
    ali fica no Google Ads (PAUSADO) pra revisao manual."""
    nome = proposta["nome_campanha"]

    budget_resource = _criar_orcamento(client, cid, nome, proposta["orcamento_diario_brl"])
    campanha_resource = _criar_campanha(client, cid, nome, budget_resource)
    _criar_targeting(client, cid, campanha_resource)
    grupo_resource = _criar_grupo_anuncio(client, cid, campanha_resource, f"{nome} — grupo 1")
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
