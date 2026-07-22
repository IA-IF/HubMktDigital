"""Carrega credenciais e caminhos do .env."""
import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)


def _obrigatoria(nome: str) -> str:
    valor = os.getenv(nome, "").strip()
    if not valor:
        raise SystemExit(
            f"Variavel {nome} nao definida no .env — copie .env.example para "
            ".env e preencha as credenciais (ver README.md)."
        )
    return valor


def ga4_credentials_config() -> dict:
    return {
        "client_id": _obrigatoria("GA4_CLIENT_ID"),
        "client_secret": _obrigatoria("GA4_CLIENT_SECRET"),
        "refresh_token": _obrigatoria("GA4_REFRESH_TOKEN"),
        "token_uri": "https://oauth2.googleapis.com/token",
    }


def ga4_property_path() -> str:
    return f"properties/{_obrigatoria('GA4_PROPERTY_ID')}"


def ga4_measurement_id() -> str:
    return _obrigatoria("GA4_MEASUREMENT_ID")
