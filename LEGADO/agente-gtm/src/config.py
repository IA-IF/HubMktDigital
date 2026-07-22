"""Carrega credenciais e caminhos do .env."""
import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = PROJECT_ROOT.parent
# SITE seleciona qual SITES/<site>/.env carregar (ex: SITE=3gfoods). Sem
# SITE, usa "integrafoods" (o site original) — nunca um .env sem nome.
# Credenciais comuns (OAuth client, LLM, Telegram) vem do .env
# compartilhado na raiz; so o que e unico do site fica em SITES/<site>/.env.
SITE = os.getenv("SITE", "").strip() or "integrafoods"
load_dotenv(REPO_ROOT / ".env")
load_dotenv(REPO_ROOT / "SITES" / SITE / ".env")

DATA_DIR = PROJECT_ROOT / "data" / SITE
DATA_DIR.mkdir(parents=True, exist_ok=True)


def _obrigatoria(nome: str) -> str:
    valor = os.getenv(nome, "").strip()
    if not valor:
        raise SystemExit(
            f"Variavel {nome} nao definida no .env — copie .env.example para "
            ".env e preencha as credenciais (ver README.md)."
        )
    return valor


def gtm_credentials_config() -> dict:
    return {
        "client_id": _obrigatoria("GTM_CLIENT_ID"),
        "client_secret": _obrigatoria("GTM_CLIENT_SECRET"),
        "refresh_token": _obrigatoria("GTM_REFRESH_TOKEN"),
        "token_uri": "https://oauth2.googleapis.com/token",
    }


def gtm_container_path() -> str:
    account_id = _obrigatoria("GTM_ACCOUNT_ID")
    container_id = _obrigatoria("GTM_CONTAINER_ID")
    return f"accounts/{account_id}/containers/{container_id}"


def ga4_measurement_id() -> str:
    return _obrigatoria("GA4_MEASUREMENT_ID")


def site_url() -> str:
    return _obrigatoria("SITE_URL")
