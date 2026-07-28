"""Registra, no Redis, um pedido que nenhuma tool disponível resolve --
em vez de o agente inventar uma resposta ou fingir ter executado algo
(regra inegociável, ver `tool.json`). Fica como fila revisável por
humano, não implementação automática.

Uso:
    echo '{"pedido": "...", "contexto": "..."}' | python registrar.py <site>
"""
import json
import sys
from datetime import datetime
from pathlib import Path

from dotenv import dotenv_values

REPO_ROOT = Path(__file__).resolve().parents[3]
CHAVE_LISTA = "pedidos_futuros"


def registrar(site: str, pedido: str, contexto: str = "") -> dict:
    env = dotenv_values(REPO_ROOT / "REDIS" / ".env")
    if not env.get("REDIS_URL"):
        return {"ok": False, "erros": ["REDIS_URL nao configurado em REDIS/.env"]}

    import redis
    cliente = redis.Redis.from_url(env["REDIS_URL"], decode_responses=True)

    registro = {
        "site": site,
        "pedido": pedido,
        "contexto": contexto,
        "criado_em": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    cliente.rpush(CHAVE_LISTA, json.dumps(registro, ensure_ascii=False))
    return {"ok": True, "status": "registrado"}


if __name__ == "__main__":
    site_arg = sys.argv[1] if len(sys.argv) > 1 else "3gfoods"
    entrada = json.load(sys.stdin)
    print(json.dumps(
        registrar(site_arg, entrada["pedido"], entrada.get("contexto", "")),
        ensure_ascii=False, indent=2,
    ))
