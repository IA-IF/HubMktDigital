"""Carrega credenciais e caminhos do .env."""
import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
# SITE seleciona qual .env.<site> carregar (ex: SITE=3gfoods). Sem SITE,
# usa .env (compatibilidade com o setup original, Integra Foods).
SITE = os.getenv("SITE", "").strip()
ENV_FILE = PROJECT_ROOT / (f".env.{SITE}" if SITE else ".env")
load_dotenv(ENV_FILE)

DATA_DIR = PROJECT_ROOT / "data" / (SITE or "integrafoods")
DATA_DIR.mkdir(parents=True, exist_ok=True)


def _obrigatoria(nome: str) -> str:
    valor = os.getenv(nome, "").strip()
    if not valor:
        raise SystemExit(
            f"Variavel {nome} nao definida no .env — copie .env.example para "
            ".env e preencha as credenciais (ver README.md)."
        )
    return valor


def sc_credentials_config() -> dict:
    return {
        "client_id": _obrigatoria("SC_CLIENT_ID"),
        "client_secret": _obrigatoria("SC_CLIENT_SECRET"),
        "refresh_token": _obrigatoria("SC_REFRESH_TOKEN"),
        "token_uri": "https://oauth2.googleapis.com/token",
    }


def sc_site_url() -> str:
    return _obrigatoria("SC_SITE_URL")
