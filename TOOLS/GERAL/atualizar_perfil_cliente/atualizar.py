"""Atualiza um campo do perfil de cliente (por site) no Redis -- mesmo
esquema de AGENTES/julio/perfil_cliente.py (hash cliente:<site>:perfil),
pra compatibilidade se algum dia precisar ler o mesmo dado de lá.
"""
import json
import sys
from pathlib import Path

from dotenv import dotenv_values

REPO_ROOT = Path(__file__).resolve().parents[3]

CAMPOS = [
    "quem_e_cliente", "o_que_vende", "pra_quem_vende",
    "publico_alvo", "orcamento_diario_tipico", "roas_alvo", "produtos_em_foco",
]


def atualizar(site: str, campo: str, valor: str) -> dict:
    if campo not in CAMPOS:
        return {"ok": False, "erros": [f"campo de perfil desconhecido: {campo!r} (validos: {CAMPOS})"]}

    env = dotenv_values(REPO_ROOT / "REDIS" / ".env")
    if not env.get("REDIS_URL"):
        return {"ok": False, "erros": ["REDIS_URL nao configurado em REDIS/.env"]}

    import redis
    cliente = redis.Redis.from_url(env["REDIS_URL"], decode_responses=True)
    cliente.hset(f"cliente:{site}:perfil", campo, valor)
    return {"ok": True}


if __name__ == "__main__":
    site_arg = sys.argv[1] if len(sys.argv) > 1 else "3gfoods"
    entrada = json.load(sys.stdin)
    print(json.dumps(atualizar(site_arg, entrada["campo"], entrada["valor"]), ensure_ascii=False, indent=2))
