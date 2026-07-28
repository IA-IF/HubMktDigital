"""Consulta ao vivo as dimensões e métricas reais disponíveis na
propriedade GA4 (via `getMetadata`, discovery document em runtime --
mais direto que Ads, que não tem esse mecanismo). Generaliza a coleta
estática que já existia (ver histórico de `learn-api`) numa tool que o
agente chama sob demanda, sem precisar de curadoria prévia de quais
dimensões/métricas "importam".

Cacheado no Redis por site -- a lista de dimensões/métricas de uma
propriedade não muda a cada request.
"""
import json
import sys
from pathlib import Path

from dotenv import dotenv_values
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

REPO_ROOT = Path(__file__).resolve().parents[3]
SCOPES = ["https://www.googleapis.com/auth/analytics.readonly"]
PREFIXO_CACHE = "ga4_schema:"


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


def _consultar_schema_sem_cache(site: str) -> dict:
    comum = dotenv_values(REPO_ROOT / ".env")
    do_site = dotenv_values(REPO_ROOT / "SITES" / site / ".env")
    if "GA4_PROPERTY_ID" not in do_site:
        return {"erro": f"site '{site}' sem GA4_PROPERTY_ID configurado"}

    creds = Credentials(
        token=None, scopes=SCOPES,
        client_id=comum["GA4_CLIENT_ID"], client_secret=comum["GA4_CLIENT_SECRET"],
        refresh_token=comum["GA4_REFRESH_TOKEN"], token_uri="https://oauth2.googleapis.com/token",
    )
    service = build("analyticsdata", "v1beta", credentials=creds, cache_discovery=False)
    property_path = f"properties/{do_site['GA4_PROPERTY_ID']}"
    meta = service.properties().getMetadata(name=f"{property_path}/metadata").execute()
    return {
        "dimensions": meta.get("dimensions", []),
        "metrics": meta.get("metrics", []),
    }


def consultar_schema(site: str) -> dict:
    cliente_redis = _cliente_redis_ou_none()
    chave = f"{PREFIXO_CACHE}{site}"

    if cliente_redis is not None:
        cacheado = cliente_redis.get(chave)
        if cacheado is not None:
            return json.loads(cacheado)

    resultado = _consultar_schema_sem_cache(site)

    if cliente_redis is not None and "erro" not in resultado:
        cliente_redis.set(chave, json.dumps(resultado, ensure_ascii=False))

    return resultado


if __name__ == "__main__":
    site_arg = sys.argv[1] if len(sys.argv) > 1 else "3gfoods"
    print(json.dumps(consultar_schema(site_arg), ensure_ascii=False, indent=2))
