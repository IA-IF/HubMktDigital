"""Carrega credenciais e guardrails do .env."""
import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
# SITE seleciona qual .env.<site>/CLAUDE.<site>.md carregar (ex: SITE=3gfoods).
# Sem SITE, usa "integrafoods" (o site original) — nunca um .env/CLAUDE.md sem nome.
SITE = os.getenv("SITE", "").strip() or "integrafoods"
ENV_FILE = PROJECT_ROOT / f".env.{SITE}"
load_dotenv(ENV_FILE)

DATA_DIR = PROJECT_ROOT / "data" / SITE
LOGS_DIR = PROJECT_ROOT / "logs" / SITE
CLAUDE_MD = PROJECT_ROOT / f"CLAUDE.{SITE}.md"
FILA_APROVACAO = DATA_DIR / "aprovacoes_pendentes.json"

DATA_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)


def _obrigatoria(nome: str) -> str:
    valor = os.getenv(nome, "").strip()
    if not valor:
        raise SystemExit(
            f"Variavel {nome} nao definida no .env — complete a Fase 1 do guia "
            "e copie .env.example para .env preenchendo as credenciais."
        )
    return valor


def google_ads_config() -> dict:
    cfg = {
        "developer_token": _obrigatoria("GOOGLE_ADS_DEVELOPER_TOKEN"),
        "client_id": _obrigatoria("GOOGLE_ADS_CLIENT_ID"),
        "client_secret": _obrigatoria("GOOGLE_ADS_CLIENT_SECRET"),
        "refresh_token": _obrigatoria("GOOGLE_ADS_REFRESH_TOKEN"),
        "use_proto_plus": True,
    }
    login_customer_id = os.getenv("GOOGLE_ADS_LOGIN_CUSTOMER_ID", "").strip()
    if login_customer_id:
        cfg["login_customer_id"] = login_customer_id
    return cfg


def customer_id() -> str:
    return _obrigatoria("GOOGLE_ADS_CUSTOMER_ID").replace("-", "")


def llm_provider() -> str:
    """'anthropic' ou 'openai' — qual API o analyst.py usa. Default openai
    porque no momento (jul/2026) so ha credito na OpenAI; troque para
    'anthropic' no .env.<site> quando quiser comparar performance."""
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


def guardrails() -> dict:
    return {
        "teto_gasto_diario": float(os.getenv("TETO_GASTO_DIARIO", "500")),
        "limite_aprovacao_diario": float(os.getenv("LIMITE_APROVACAO_DIARIO", "100")),
        "max_mudanca_orcamento_pct": float(os.getenv("MAX_MUDANCA_ORCAMENTO_PCT", "20")),
        "acoes_permitidas": {
            "pausar_keyword",
            "ajustar_lance",
            "ajustar_orcamento",
            "negativar_termo",
        },
    }
