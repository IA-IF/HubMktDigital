"""Fase D do esquema de analise de vendas (PARCIAL) -- ver
docs/superpowers/specs/2026-07-22-esquema-analise-vendas-design.md.

So a parte de crawlability/indexacao (Search Console API). Core Web
Vitals fica BLOQUEADO nesta sessao: depende do plugin chrome-devtools-mcp
(Lighthouse rodando navegador de verdade) ou Playwright, e nenhum dos
dois esta conectado agora. Quando reconectar, essa e a proxima peca a
implementar aqui -- nao inventar numero de performance sem rodar o
navegador de verdade.

Uso:
    python analise_tecnica.py [site]
    python analise_tecnica.py 3gfoods
"""
import json
import sys
from pathlib import Path

from dotenv import dotenv_values
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tecnica import calcular_saude_sitemaps  # noqa: E402

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


def rodar_analise_tecnica(site: str) -> dict:
    service, site_url = _service_e_site_url(site)
    resposta = service.sitemaps().list(siteUrl=site_url).execute()

    return {
        "site": site,
        "indexacao": calcular_saude_sitemaps(resposta),
        "core_web_vitals": {
            "status": "BLOQUEADO",
            "motivo": (
                "chrome-devtools-mcp/Playwright nao conectados nesta sessao — "
                "Core Web Vitals precisa de navegador real (Lighthouse), nao e "
                "chamada de API. Rodar quando o plugin estiver disponivel."
            ),
        },
    }


if __name__ == "__main__":
    site_arg = sys.argv[1] if len(sys.argv) > 1 else "3gfoods"
    print(json.dumps(rodar_analise_tecnica(site_arg), ensure_ascii=False, indent=2))
