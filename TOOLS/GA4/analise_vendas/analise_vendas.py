"""Fase A do esquema de analise de vendas (GA4 sozinho) -- ver
docs/superpowers/specs/2026-07-22-esquema-analise-vendas-design.md.

Uso:
    python analise_vendas.py [site] [dias]
    python analise_vendas.py 3gfoods 7

Credenciais so da raiz do projeto (.env + SITES/<site>/.env), nunca de
LEGADO/ -- mesma regra de TOOLS/GA4/DOCS/README.md.
"""
import json
import sys
from pathlib import Path

from dotenv import dotenv_values
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

sys.path.insert(0, str(Path(__file__).resolve().parent))

from canais import calcular_split_canal
from coleta import buscar_contagens_funil, buscar_dados_ecommerce, buscar_linhas_canal
from ecommerce_taxas import calcular_taxas_ecommerce
from funil import calcular_funil

REPO_ROOT = Path(__file__).resolve().parents[3]  # TOOLS/GA4/analise_vendas -> raiz do projeto
SCOPES = ["https://www.googleapis.com/auth/analytics.readonly"]


def _service_e_property(site: str):
    comum = dotenv_values(REPO_ROOT / ".env")
    do_site = dotenv_values(REPO_ROOT / "SITES" / site / ".env")
    if "GA4_PROPERTY_ID" not in do_site:
        raise SystemExit(
            f"Site '{site}' nao tem GA4_PROPERTY_ID configurado — confirme que "
            f"SITES/{site}/.env existe e tem essa variavel."
        )
    creds = Credentials(
        token=None, scopes=SCOPES,
        client_id=comum["GA4_CLIENT_ID"], client_secret=comum["GA4_CLIENT_SECRET"],
        refresh_token=comum["GA4_REFRESH_TOKEN"], token_uri="https://oauth2.googleapis.com/token",
    )
    service = build("analyticsdata", "v1beta", credentials=creds, cache_discovery=False)
    property_path = f"properties/{do_site['GA4_PROPERTY_ID']}"
    return service, property_path


def rodar_analise(site: str, dias: int = 7) -> dict:
    service, property_path = _service_e_property(site)

    contagens_funil = buscar_contagens_funil(service, property_path, dias)
    linhas_canal = buscar_linhas_canal(service, property_path, dias)
    dados_ecommerce = buscar_dados_ecommerce(service, property_path, dias)

    return {
        "site": site,
        "periodo_dias": dias,
        "funil": calcular_funil(contagens_funil),
        "canais": calcular_split_canal(linhas_canal),
        "taxas_ecommerce": calcular_taxas_ecommerce(dados_ecommerce),
    }


if __name__ == "__main__":
    site_arg = sys.argv[1] if len(sys.argv) > 1 else "3gfoods"
    dias_arg = int(sys.argv[2]) if len(sys.argv) > 2 else 7
    print(json.dumps(rodar_analise(site_arg, dias_arg), ensure_ascii=False, indent=2))
