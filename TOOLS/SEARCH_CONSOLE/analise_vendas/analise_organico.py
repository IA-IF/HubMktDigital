"""Fase C do esquema de analise de vendas (Search Console + GA4) -- ver
docs/superpowers/specs/2026-07-22-esquema-analise-vendas-design.md.

Uso:
    python analise_organico.py [site] [dias] [termos_marca separados por virgula]
    python analise_organico.py 3gfoods 7 "3g foods,3gfoods"

Credenciais so da raiz do projeto (.env + SITES/<site>/.env).
"""
import json
import sys
from datetime import date, timedelta
from pathlib import Path

from dotenv import dotenv_values
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "GA4" / "analise_vendas"))

from organico import calcular_resumo_organico, calcular_split_marca  # noqa: E402
from analise_vendas import rodar_analise as rodar_analise_ga4  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]
SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]


def _service_e_site_url(site: str):
    comum = dotenv_values(REPO_ROOT / ".env")
    do_site = dotenv_values(REPO_ROOT / "SITES" / site / ".env")
    if "SC_SITE_URL" not in do_site:
        raise SystemExit(
            f"Site '{site}' nao tem SC_SITE_URL configurado — confirme que "
            f"SITES/{site}/.env existe e tem essa variavel."
        )
    creds = Credentials(
        token=None, scopes=SCOPES,
        client_id=comum["SC_CLIENT_ID"], client_secret=comum["SC_CLIENT_SECRET"],
        refresh_token=comum["SC_REFRESH_TOKEN"], token_uri="https://oauth2.googleapis.com/token",
    )
    service = build("searchconsole", "v1", credentials=creds, cache_discovery=False)
    return service, do_site["SC_SITE_URL"]


def buscar_queries(service, site_url: str, dias: int) -> list[dict]:
    hoje = date.today()
    corpo = {
        "startDate": (hoje - timedelta(days=dias)).isoformat(),
        "endDate": hoje.isoformat(),
        "dimensions": ["query"],
        "rowLimit": 250,
    }
    resp = service.searchanalytics().query(siteUrl=site_url, body=corpo).execute()
    linhas = []
    for row in resp.get("rows", []):
        linhas.append({
            "query": row["keys"][0],
            "clicks": row["clicks"],
            "impressions": row["impressions"],
            "position": row["position"],
        })
    return linhas


def rodar_analise_organico(site: str, dias: int = 7, termos_marca: list[str] | None = None) -> dict:
    if termos_marca is None:
        termos_marca = []

    service, site_url = _service_e_site_url(site)
    linhas = buscar_queries(service, site_url, dias)

    dados_ga4 = rodar_analise_ga4(site, dias)
    canal_organico = next(
        (c for c in dados_ga4["canais"] if c["canal"] == "Organic Search"), None
    )

    return {
        "site": site,
        "periodo_dias": dias,
        "resumo_organico": calcular_resumo_organico(linhas),
        "split_marca": calcular_split_marca(linhas, [t.lower() for t in termos_marca]),
        "sessoes_organicas_ga4": canal_organico["sessoes"] if canal_organico else 0,
        "compras_organicas_ga4": canal_organico["compras"] if canal_organico else 0,
    }


if __name__ == "__main__":
    site_arg = sys.argv[1] if len(sys.argv) > 1 else "3gfoods"
    dias_arg = int(sys.argv[2]) if len(sys.argv) > 2 else 7
    termos_arg = sys.argv[3].split(",") if len(sys.argv) > 3 else []
    print(json.dumps(
        rodar_analise_organico(site_arg, dias_arg, termos_arg), ensure_ascii=False, indent=2
    ))
