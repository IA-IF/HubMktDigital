"""Gera o refresh_token da Tag Manager API (leitura).

Uso:
    python generate_refresh_token_gtm.py

Pode reaproveitar o mesmo client_id/client_secret do projeto Cloud interno
usado pelo Ads (ver ..\\agente-cmo\\docs\\setup-do-zero-checklist.md) — so
precisa autorizar de novo porque o scope e diferente (tagmanager.readonly em
vez de adwords). Requer GTM_CLIENT_ID e GTM_CLIENT_SECRET no .env (ou
digitados quando solicitado). Abre o navegador para autorizar e imprime o
refresh_token — copie-o para o .env.

A conta que autorizar precisa ter acesso de leitura ao container GTM
(accounts/<GTM_ACCOUNT_ID>/containers/<GTM_CONTAINER_ID> no .env) — confirme
isso em https://tagmanager.google.com antes de rodar.
"""
import os

from dotenv import load_dotenv
from google_auth_oauthlib.flow import InstalledAppFlow

load_dotenv()

SCOPES = ["https://www.googleapis.com/auth/tagmanager.readonly"]


def main() -> None:
    client_id = os.getenv("GTM_CLIENT_ID") or input("Client ID: ").strip()
    client_secret = os.getenv("GTM_CLIENT_SECRET") or input("Client Secret: ").strip()

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
    print(f"GTM_REFRESH_TOKEN={credentials.refresh_token}")


if __name__ == "__main__":
    main()
