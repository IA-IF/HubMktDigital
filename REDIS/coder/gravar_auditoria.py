"""Persiste snapshot de auditoria (ex: indexacao Search Console) no
Redis, pra virar historico comparavel entre rodadas.

Schema:
    auditoria:<tipo>:<site>:<timestamp ISO>   -- SET, JSON string (snapshot)
    auditoria:<tipo>:<site>:historico          -- RPUSH, lista de timestamps

Uso:
    echo '{...snapshot...}' | python gravar_auditoria.py <tipo> <site>
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import redis
from dotenv import dotenv_values

REPO_ROOT = Path(__file__).resolve().parents[2]


def gravar(cliente_redis, tipo: str, site: str, snapshot: dict) -> str:
    timestamp = datetime.now(timezone.utc).isoformat()
    chave_snapshot = f"auditoria:{tipo}:{site}:{timestamp}"
    chave_historico = f"auditoria:{tipo}:{site}:historico"

    cliente_redis.set(chave_snapshot, json.dumps(snapshot, ensure_ascii=False))
    cliente_redis.rpush(chave_historico, timestamp)

    return timestamp


if __name__ == "__main__":
    tipo_arg = sys.argv[1]
    site_arg = sys.argv[2]
    snapshot_entrada = json.load(sys.stdin)

    comum = dotenv_values(REPO_ROOT / "REDIS" / ".env")
    cliente = redis.from_url(comum["REDIS_URL"], decode_responses=True)

    ts = gravar(cliente, tipo_arg, site_arg, snapshot_entrada)
    print(json.dumps({"ok": True, "chave": f"auditoria:{tipo_arg}:{site_arg}:{ts}"}, ensure_ascii=False))
