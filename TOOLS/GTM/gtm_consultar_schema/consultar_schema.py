"""Consulta ao vivo o discovery document da API do GTM -- recursos
(inclusive aninhados, ex: accounts.containers.workspaces.tags),
métodos e parâmetros reais. Cacheado no Redis (discovery document não
muda entre chamadas).
"""
import json
import sys
from pathlib import Path

from dotenv import dotenv_values
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

REPO_ROOT = Path(__file__).resolve().parents[3]
SCOPES = ["https://www.googleapis.com/auth/tagmanager.readonly"]
CHAVE_CACHE = "gtm_schema:discovery"


def _cliente_redis_ou_none():
    try:
        import redis
        env = dotenv_values(REPO_ROOT / "REDIS" / ".env")
        if not env.get("REDIS_URL"):
            return None
        cliente = redis.Redis.from_url(env["REDIS_URL"], decode_responses=True)
        cliente.ping()
        return cliente
    except Exception:
        return None


def _listar_recursos(recursos: dict, prefixo: str = "") -> dict:
    achatado = {}
    for nome, recurso in recursos.items():
        caminho = f"{prefixo}{nome}"
        achatado[caminho] = {
            "methods": {
                nome_metodo: {
                    "description": metodo.get("description"),
                    "httpMethod": metodo.get("httpMethod"),
                    "parameters": metodo.get("parameters", {}),
                    "request": metodo.get("request"),
                }
                for nome_metodo, metodo in recurso.get("methods", {}).items()
            }
        }
        if "resources" in recurso:
            achatado.update(_listar_recursos(recurso["resources"], f"{caminho}."))
    return achatado


def _consultar_schema_sem_cache() -> dict:
    comum = dotenv_values(REPO_ROOT / ".env")
    creds = Credentials(
        token=None, scopes=SCOPES,
        client_id=comum["GTM_CLIENT_ID"], client_secret=comum["GTM_CLIENT_SECRET"],
        refresh_token=comum["GTM_REFRESH_TOKEN"], token_uri="https://oauth2.googleapis.com/token",
    )
    service = build("tagmanager", "v2", credentials=creds, cache_discovery=False)
    desc = service._rootDesc
    return {"resources": _listar_recursos(desc.get("resources", {}))}


def consultar_schema() -> dict:
    cliente_redis = _cliente_redis_ou_none()
    if cliente_redis is not None:
        cacheado = cliente_redis.get(CHAVE_CACHE)
        if cacheado is not None:
            return json.loads(cacheado)

    resultado = _consultar_schema_sem_cache()

    if cliente_redis is not None:
        cliente_redis.set(CHAVE_CACHE, json.dumps(resultado, ensure_ascii=False))

    return resultado


if __name__ == "__main__":
    print(json.dumps(consultar_schema(), ensure_ascii=False, indent=2))
