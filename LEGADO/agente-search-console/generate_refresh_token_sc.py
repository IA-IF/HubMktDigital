"""Gera o refresh_token da Search Console API (leitura).

Uso:
    python generate_refresh_token_sc.py

Pode reaproveitar o mesmo client_id/client_secret do projeto Cloud interno
usado pelo Ads/GTM/GA4 (agente-cmo-ads-interno) — so precisa autorizar de
novo porque o scope e diferente (webmasters.readonly). Requer SC_CLIENT_ID e
SC_CLIENT_SECRET no .env (ou digitados quando solicitado). Abre o navegador
para autorizar e imprime o refresh_token — copie-o para o .env.

A conta que autorizar precisa ter acesso a propriedade
(SC_SITE_URL no .env) — confirme isso em https://search.google.com/search-console
antes de rodar.
"""
import os

from dotenv import load_dotenv
from google_auth_oauthlib.flow import InstalledAppFlow

load_dotenv()

SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]


def main() -> None:
    client_id = os.getenv("SC_CLIENT_ID") or input("Client ID: ").strip()
    client_secret = os.getenv("SC_CLIENT_SECRET") or input("Client Secret: ").strip()

    flow = InstalledAppFlow.from_client_config(
        {
            "installed": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=SCOPES,
    )
    credentials = flow.run_local_server(port=0)

    print("\n=== Copie para o seu .env ===")
    print(f"SC_REFRESH_TOKEN={credentials.refresh_token}")


if __name__ == "__main__":
    main()
