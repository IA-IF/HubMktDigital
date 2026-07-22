"""Carrega credenciais do .env compartilhado em REDIS/ (um nivel acima)."""
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
            f"Variavel {nome} nao definida — confira REDIS/.env "
            "(copie de REDIS/.env.example se ainda nao existir)."
        )
    return valor


def redis_url() -> str:
    return _obrigatoria("REDIS_URL")


def anthropic_api_key() -> str:
    return _obrigatoria("ANTHROPIC_API_KEY")


def simple_model() -> str:
    return os.getenv("LLM_ROUTER_SIMPLE_MODEL", "claude-haiku-4-5-20251001")


def complex_model() -> str:
    return os.getenv("LLM_ROUTER_COMPLEX_MODEL", "claude-sonnet-4-6")
