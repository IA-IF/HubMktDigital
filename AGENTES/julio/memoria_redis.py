"""Memoria de conversa em Redis -- substitui os JSONs locais por chat
(antes em data/telegram_conversas/ e data/conversas_elis/, separados por
agente; agora um so, porque os dois agentes viraram um so -- ver plano
docs/superpowers/plans/2026-07-27-fusao-agente-fluxo-conversa.md).

Mesmo padrao de conexao que discover_tool.py (REDIS_URL de
REDIS/llm_router/config.py). So chave simples (get/set de JSON) por
enquanto -- indexacao semantica do historico (busca vetorial) fica pra
quando alguem precisar de fato buscar "o que a gente falou sobre X mes
passado"; nao vale a latencia de carregar o modelo de embedding em toda
mensagem so por precaucao.
"""
import json
import sys
from pathlib import Path

import redis

HUB_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HUB_ROOT / "REDIS" / "llm_router"))
import config as llm_config  # noqa: E402

PREFIXO_ESTADO = "conversa:estado:"
PREFIXO_RESUMO = "conversa:resumo:"


def _client() -> redis.Redis:
    return redis.Redis.from_url(llm_config.redis_url(), decode_responses=True)


def carregar_estado(chat_id: str, estado_vazio: dict) -> dict:
    bruto = _client().get(f"{PREFIXO_ESTADO}{chat_id}")
    if bruto is None:
        return estado_vazio
    return json.loads(bruto)


def salvar_estado(chat_id: str, estado: dict) -> None:
    _client().set(f"{PREFIXO_ESTADO}{chat_id}", json.dumps(estado, ensure_ascii=False))


def carregar_resumo(chat_id: str) -> str:
    return _client().get(f"{PREFIXO_RESUMO}{chat_id}") or ""


def salvar_resumo(chat_id: str, resumo: str) -> None:
    _client().set(f"{PREFIXO_RESUMO}{chat_id}", resumo)
