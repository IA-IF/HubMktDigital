"""Cria/atualiza/remove QUALQUER recurso do Google Ads através do
mecanismo genérico que a própria API já oferece pra isso --
GoogleAdsService.Mutate com MutateOperation (um wrapper que aceita
qualquer tipo de operação via oneof). Substitui a abordagem de uma
tool por capacidade (TOOLS/ADWORDS/criar_campanha) por um único
executor que o agente usa pra QUALQUER recurso, informado por
ads_consultar_schema.

Guardrail inegociável preservado (igual criar_campanha): Campaign
criada aqui sempre nasce PAUSED, mesmo que campos peça outra coisa --
ativar é sempre decisão manual fora desta tool.
"""
import importlib
import json
import pkgutil
import re
import sys
from pathlib import Path

import google.ads.googleads.v24 as v24_pkg
from dotenv import dotenv_values
from google.ads.googleads.client import GoogleAdsClient

REPO_ROOT = Path(__file__).resolve().parents[3]

# Índice de classes de mensagem protobuf indexável por nome -- mesma
# técnica de TOOLS/ADWORDS/ads_consultar_schema/consultar_schema.py,
# duplicada aqui (não importada de lá) de propósito: cada tool é um
# processo independente, ver AGENTES/julio/agentes.py docstring.
_INDICE_CLASSES: dict[str, type] = {}


def _indexar_classes() -> None:
    if _INDICE_CLASSES:
        return
    for _, nome_modulo, _ in pkgutil.walk_packages(v24_pkg.__path__, prefix="google.ads.googleads.v24."):
        if ".types" not in nome_modulo:
            continue
        try:
            mod = importlib.import_module(nome_modulo)
        except Exception:
            continue
        for atributo in dir(mod):
            if atributo.startswith("_") or atributo in _INDICE_CLASSES:
                continue
            obj = getattr(mod, atributo)
            if hasattr(obj, "pb") and callable(getattr(obj, "pb", None)):
                try:
                    if hasattr(obj.pb(), "DESCRIPTOR"):
                        _INDICE_CLASSES[atributo] = obj
                except Exception:
                    continue


def nome_campo_operacao(recurso: str) -> str:
    """'CampaignCriterion' -> 'campaign_criterion_operation'."""
    snake = re.sub(r"(?<!^)(?=[A-Z])", "_", recurso).lower()
    return f"{snake}_operation"


def aplicar_campos(mensagem, campos: dict) -> None:
    for chave, valor in campos.items():
        if isinstance(valor, dict):
            aplicar_campos(getattr(mensagem, chave), valor)
        else:
            setattr(mensagem, chave, valor)


def montar_mutate_operation(recurso: str, operacao: str, campos: dict):
    _indexar_classes()
    from google.ads.googleads.v24.services.types.google_ads_service import MutateOperation

    nome_operation = f"{recurso}Operation"
    classe_operation = _INDICE_CLASSES.get(nome_operation)
    if classe_operation is None:
        raise ValueError(f"tipo de operacao desconhecido: {nome_operation}")

    op = classe_operation()
    campos_finais = dict(campos)
    if recurso == "Campaign" and operacao == "create":
        campos_finais["status"] = "PAUSED"

    if operacao == "create":
        aplicar_campos(op.create, campos_finais)
    elif operacao == "update":
        aplicar_campos(op.update, campos_finais)
    elif operacao == "remove":
        op.remove = campos_finais["resource_name"]
    else:
        raise ValueError(f"operacao desconhecida: {operacao}")

    mutate_op = MutateOperation()
    setattr(mutate_op, nome_campo_operacao(recurso), op)
    return mutate_op


def executar_mutate(site: str, recurso: str, operacao: str, campos: dict) -> dict:
    comum = dotenv_values(REPO_ROOT / ".env")
    do_site = dotenv_values(REPO_ROOT / "SITES" / site / ".env")
    if "GOOGLE_ADS_CUSTOMER_ID" not in do_site or not do_site["GOOGLE_ADS_CUSTOMER_ID"]:
        return {"ok": False, "erros": [f"site '{site}' sem GOOGLE_ADS_CUSTOMER_ID configurado"]}

    cfg = {
        "developer_token": comum["GOOGLE_ADS_DEVELOPER_TOKEN"],
        "client_id": comum["GOOGLE_ADS_CLIENT_ID"],
        "client_secret": comum["GOOGLE_ADS_CLIENT_SECRET"],
        "refresh_token": comum["GOOGLE_ADS_REFRESH_TOKEN"],
        "use_proto_plus": True,
    }
    if comum.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID"):
        cfg["login_customer_id"] = comum["GOOGLE_ADS_LOGIN_CUSTOMER_ID"]
    client = GoogleAdsClient.load_from_dict(cfg)
    cid = do_site["GOOGLE_ADS_CUSTOMER_ID"].replace("-", "")

    try:
        mutate_op = montar_mutate_operation(recurso, operacao, campos)
    except ValueError as exc:
        return {"ok": False, "erros": [str(exc)]}

    service = client.get_service("GoogleAdsService")
    try:
        resposta = service.mutate(customer_id=cid, mutate_operations=[mutate_op])
    except Exception as exc:  # noqa: BLE001 -- GoogleAdsException tem forma variavel
        return {"ok": False, "erros": [str(exc)]}

    resultado = resposta.mutate_operation_responses[0]
    campo_resposta = resultado._pb.WhichOneof("response")
    resource_name = getattr(getattr(resultado, campo_resposta), "resource_name", None)
    return {"ok": True, "resource_name": resource_name}


if __name__ == "__main__":
    site_arg = sys.argv[1] if len(sys.argv) > 1 else "3gfoods"
    entrada = json.load(sys.stdin)
    print(json.dumps(
        executar_mutate(site_arg, entrada["recurso"], entrada["operacao"], entrada["campos"]),
        ensure_ascii=False, indent=2,
    ))
