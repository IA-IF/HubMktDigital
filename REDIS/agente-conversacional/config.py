"""Carrega credenciais do .env em REDIS/ (um nivel acima deste pacote)."""
import os
from pathlib import Path

from dotenv import load_dotenv

PACKAGE_ROOT = Path(__file__).resolve().parent
REDIS_ROOT = PACKAGE_ROOT.parent
ENV_FILE = REDIS_ROOT / ".env"
load_dotenv(ENV_FILE)


def _obrigatoria(nome: str) -> str:
    valor = os.getenv(nome, "").strip()
    if not valor:
        raise SystemExit(
            f"Variavel {nome} nao definida — copie REDIS/.env.example para "
            "REDIS/.env e preencha as credenciais."
        )
    return valor


def redis_url() -> str:
    return _obrigatoria("REDIS_URL")


def anthropic_api_key() -> str:
    return _obrigatoria("ANTHROPIC_API_KEY")


def claude_model() -> str:
    return os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")
