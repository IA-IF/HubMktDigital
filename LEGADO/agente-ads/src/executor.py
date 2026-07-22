"""Valida ações contra os guardrails e executa via Google Ads API (Prompt 4 do guia).

- Modo --dry-run: apenas simula, nada é alterado.
- Ações acima de LIMITE_APROVACAO_DIARIO ou fora da lista permitida vão para
  a fila de aprovação (aprovacoes_pendentes.json) em vez de executar.
"""
import json
from datetime import datetime

from google.ads.googleads.client import GoogleAdsClient

from src import config


def _validar(acao: dict, guardrails: dict) -> str | None:
    """Retorna o motivo para ir à fila de aprovação, ou None se pode executar."""
    if acao["acao"] not in guardrails["acoes_permitidas"]:
        return f"Acao '{acao['acao']}' fora da lista permitida"
    if acao["impacto_estimado_diario_brl"] > guardrails["limite_aprovacao_diario"]:
        return (f"Impacto estimado R$ {acao['impacto_estimado_diario_brl']:.2f}/dia "
                f"acima do limite de R$ {guardrails['limite_aprovacao_diario']:.2f}")
    if acao["acao"] == "ajustar_orcamento" and acao.get("valor_atual"):
        variacao = abs(acao["valor_novo"] - acao["valor_atual"]) / acao["valor_atual"] * 100
        if variacao > guardrails["max_mudanca_orcamento_pct"]:
            return (f"Variacao de orcamento de {variacao:.0f}% acima do maximo "
                    f"de {guardrails['max_mudanca_orcamento_pct']:.0f}%")
    return None


def _pausar_keyword(client: GoogleAdsClient, cid: str, acao: dict) -> None:
    campanha_id, grupo_id, criterio_id = acao["id_entidade"].split("/")
    service = client.get_service("AdGroupCriterionService")
    op = client.get_type("AdGroupCriterionOperation")
    criterion = op.update
    criterion.resource_name = service.ad_group_criterion_path(cid, grupo_id, criterio_id)
    criterion.status = client.enums.AdGroupCriterionStatusEnum.PAUSED
    client.copy_from(op.update_mask, client.get_type("FieldMask")(paths=["status"]))
    service.mutate_ad_group_criteria(customer_id=cid, operations=[op])


def _ajustar_lance(client: GoogleAdsClient, cid: str, acao: dict) -> None:
    campanha_id, grupo_id, criterio_id = acao["id_entidade"].split("/")
    service = client.get_service("AdGroupCriterionService")
    op = client.get_type("AdGroupCriterionOperation")
    criterion = op.update
    criterion.resource_name = service.ad_group_criterion_path(cid, grupo_id, criterio_id)
    criterion.cpc_bid_micros = int(acao["valor_novo"] * 1_000_000)
    client.copy_from(op.update_mask, client.get_type("FieldMask")(paths=["cpc_bid_micros"]))
    service.mutate_ad_group_criteria(customer_id=cid, operations=[op])


def _ajustar_orcamento(client: GoogleAdsClient, cid: str, acao: dict) -> None:
    ga_service = client.get_service("GoogleAdsService")
    campanha_id = acao["id_entidade"].split("/")[0]
    query = (f"SELECT campaign.campaign_budget FROM campaign "
             f"WHERE campaign.id = {campanha_id}")
    budget_resource = None
    for row in ga_service.search(customer_id=cid, query=query):
        budget_resource = row.campaign.campaign_budget
    if not budget_resource:
        raise ValueError(f"Orcamento da campanha {campanha_id} nao encontrado")

    service = client.get_service("CampaignBudgetService")
    op = client.get_type("CampaignBudgetOperation")
    budget = op.update
    budget.resource_name = budget_resource
    budget.amount_micros = int(acao["valor_novo"] * 1_000_000)
    client.copy_from(op.update_mask, client.get_type("FieldMask")(paths=["amount_micros"]))
    service.mutate_campaign_budgets(customer_id=cid, operations=[op])


_EXECUTORES = {
    "pausar_keyword": _pausar_keyword,
    "ajustar_lance": _ajustar_lance,
    "ajustar_orcamento": _ajustar_orcamento,
    # negativar_termo exige lista de negativas — mantido na fila de aprovacao
}


def executar(analise: dict, dry_run: bool = True) -> dict:
    guardrails = config.guardrails()
    resultado = {"executadas": [], "pendentes_aprovacao": [], "erros": []}

    client = None
    cid = None
    if not dry_run:
        client = GoogleAdsClient.load_from_dict(config.google_ads_config())
        cid = config.customer_id()

    for acao in analise.get("acoes", []):
        motivo = _validar(acao, guardrails)
        if motivo is None and acao["acao"] not in _EXECUTORES:
            motivo = f"Acao '{acao['acao']}' sem executor automatico implementado"

        if motivo:
            resultado["pendentes_aprovacao"].append({**acao, "motivo_aprovacao": motivo})
            continue

        if dry_run:
            resultado["executadas"].append({**acao, "modo": "dry-run (simulado)"})
            continue

        try:
            _EXECUTORES[acao["acao"]](client, cid, acao)
            resultado["executadas"].append({**acao, "modo": "executado"})
        except Exception as exc:  # noqa: BLE001 — registrar e seguir para a próxima ação
            resultado["erros"].append({**acao, "erro": str(exc)})

    if resultado["pendentes_aprovacao"]:
        fila = []
        if config.FILA_APROVACAO.exists():
            fila = json.loads(config.FILA_APROVACAO.read_text(encoding="utf-8"))
        fila.extend(
            {**a, "enfileirada_em": datetime.now().isoformat(timespec="seconds")}
            for a in resultado["pendentes_aprovacao"]
        )
        config.FILA_APROVACAO.write_text(
            json.dumps(fila, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    return resultado
