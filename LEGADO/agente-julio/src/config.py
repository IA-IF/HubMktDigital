"""Carrega credenciais do .env.

Diferente dos outros agentes (agente-ads, agente-gtm, ...), o Julio NAO e
site-scoped por variavel de ambiente: um unico processo atende aos 3 sites,
e e o proprio Julio quem pergunta ao humano qual site tratar em cada
conversa (ver orchestrator.py). As credenciais aqui (LLM, Telegram) sao as
mesmas nos 3 sites mesmo, por isso vem direto do .env compartilhado na
raiz do projeto (../.env) — nao ha um agente-julio/.env proprio.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
HUB_ROOT = PROJECT_ROOT.parent
ENV_FILE = HUB_ROOT / ".env"
load_dotenv(ENV_FILE)

DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# main.py dos agentes que sabem executar/consultar de fato.
AGENTE_ADS_MAIN = HUB_ROOT / "agente-ads" / "main.py"
AGENTE_GA4_MAIN = HUB_ROOT / "agente-ga4" / "main.py"

# Backlog de pedidos que o Julio ainda nao sabe atender (ver src/pedidos.py).
# Fica versionado no git de proposito (nao e data/ efemero de conversa) —
# e um documento de trabalho pra revisar junto, nao estado descartavel.
PEDIDOS_FUTUROS = PROJECT_ROOT / "pedidos-futuros.md"

# Sites conhecidos: slug (usado no SITE dos outros agentes e no nome do
# CLAUDE.<slug>.md) -> apelidos que o humano pode usar pra escolher no chat.
SITES = {
    "integrafoods": ["integrafoods", "integra foods", "integra", "if"],
    "3gfoods": ["3gfoods", "3g foods", "3g"],
    "adoro": ["adoro"],
}

# Nome bonito pra exibir de volta pro humano (slug -> nome).
SITE_NOMES = {
    "integrafoods": "Integra Foods",
    "3gfoods": "3G Foods",
    "adoro": "Adoro",
}


def claude_md(site: str) -> Path:
    """Briefing de negocio do site — lido de ../agente-ads, nao duplicado aqui
    pra nao correr o risco do Julio aprovar algo que o agente-ads rejeitaria."""
    return HUB_ROOT / "agente-ads" / f"CLAUDE.{site}.md"


def _obrigatoria(nome: str) -> str:
    valor = os.getenv(nome, "").strip()
    if not valor:
        raise SystemExit(
            f"Variavel {nome} nao definida em .env — copie .env.example "
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
