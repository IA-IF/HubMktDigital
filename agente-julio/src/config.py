"""Carrega credenciais do .env — mesmo padrao multi-site dos outros agentes."""
import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
HUB_ROOT = PROJECT_ROOT.parent
# SITE seleciona qual .env.<site> carregar (ex: SITE=3gfoods). Sem SITE,
# usa "integrafoods" — nunca um .env sem nome (ver ../agente-ads/src/config.py).
SITE = os.getenv("SITE", "").strip() or "integrafoods"
ENV_FILE = PROJECT_ROOT / f".env.{SITE}"
load_dotenv(ENV_FILE)

DATA_DIR = PROJECT_ROOT / "data" / SITE
DATA_DIR.mkdir(parents=True, exist_ok=True)

# O briefing de negocio (ticket medio, margem, guardrails) e o mesmo que o
# agente-ads usa — nao duplicamos aqui pra nao correr o risco de um agente
# aprovar algo que o outro rejeitaria.
CLAUDE_MD = HUB_ROOT / "agente-ads" / f"CLAUDE.{SITE}.md"

# main.py deste agente que sabe criar campanhas de fato.
AGENTE_ADS_MAIN = HUB_ROOT / "agente-ads" / "main.py"


def _obrigatoria(nome: str) -> str:
    valor = os.getenv(nome, "").strip()
    if not valor:
        raise SystemExit(
            f"Variavel {nome} nao definida em .env.{SITE} — copie .env.example "
            "e preencha as credenciais."
        )
    return valor


def llm_provider() -> str:
    """'anthropic' ou 'openai' — mesma logica de ../agente-ads/src/config.py."""
    return os.getenv("LLM_PROVIDER", "openai").strip().lower()


def anthropic_api_key() -> str:
    return _obrigatoria("ANTHROPIC_API_KEY")


def claude_model() -> str:
    return os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")


def openai_api_key() -> str:
    return _obrigatoria("OPENAI_API_KEY")


def openai_model() -> str:
    return os.getenv("OPENAI_MODEL", "gpt-5-mini")


def telegram_bot_token() -> str:
    return _obrigatoria("TELEGRAM_BOT_TOKEN")


def telegram_authorized_chat_ids() -> set[str]:
    bruto = os.getenv("TELEGRAM_AUTHORIZED_CHAT_IDS", "").strip()
    return {c.strip() for c in bruto.split(",") if c.strip()}
