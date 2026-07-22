"""Gera o refresh_token do Google Ads via fluxo OAuth (Fase 1.4 do guia).

Uso:
    python generate_refresh_token.py

Requer GOOGLE_ADS_CLIENT_ID e GOOGLE_ADS_CLIENT_SECRET no .env
(ou digitados quando solicitado). Abre o navegador para autorizar
e imprime o refresh_token — copie-o para o .env.
"""
import os

from dotenv import load_dotenv
from google_auth_oauthlib.flow import InstalledAppFlow

load_dotenv()

SCOPES = ["https://www.googleapis.com/auth/adwords"]


def main() -> None:
    client_id = os.getenv("GOOGLE_ADS_CLIENT_ID") or input("Client ID: ").strip()
    client_secret = os.getenv("GOOGLE_ADS_CLIENT_SECRET") or input("Client Secret: ").strip()

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
    print(f"GOOGLE_ADS_REFRESH_TOKEN={credentials.refresh_token}")


if __name__ == "__main__":
    main()
