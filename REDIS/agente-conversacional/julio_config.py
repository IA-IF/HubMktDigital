"""Config do Julio (parte conversacional: Telegram, selecao de site, tools).

Nome do modulo deliberadamente diferente de "config" — esse nome ja e
usado por ../llm_router/config.py, e o cache de modulos do Python e por
nome (nao por caminho); ter dois arquivos chamados "config.py" no mesmo
processo faria um pisar no outro dependendo da ordem de import.

Credenciais compartilhadas (Anthropic, Telegram) vem de REDIS/.env, mesmo
arquivo que o llm_router ja usa — nao duplicado, so carregado de novo aqui
(load_dotenv de novo no mesmo arquivo e inofensivo).
"""
import os
from pathlib import Path

from dotenv import load_dotenv

PACKAGE_ROOT = Path(__file__).resolve().parent
REDIS_ROOT = PACKAGE_ROOT.parent
HUB_ROOT = REDIS_ROOT.parent
ENV_FILE = REDIS_ROOT / ".env"
load_dotenv(ENV_FILE)

DATA_DIR = PACKAGE_ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# main.py dos agentes que sabem executar/consultar de fato — ainda vivem em
# LEGADO/ ate a Fase 1 (skill-ificar) do plano.
AGENTE_ADS_MAIN = HUB_ROOT / "LEGADO" / "agente-ads" / "main.py"
AGENTE_GA4_MAIN = HUB_ROOT / "LEGADO" / "agente-ga4" / "main.py"

# Continua o mesmo backlog do agente-julio (nao fragmentar historico —
# ja tem pedidos reais registrados, incluindo o do gestor da 3G Foods).
PEDIDOS_FUTUROS = HUB_ROOT / "LEGADO" / "agente-julio" / "pedidos-futuros.md"

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
    """Briefing de negocio do site — lido de LEGADO/agente-ads, nao duplicado
    aqui pra nao correr o risco do Julio aprovar algo que o agente-ads
    rejeitaria."""
    return HUB_ROOT / "LEGADO" / "agente-ads" / f"CLAUDE.{site}.md"


def _obrigatoria(nome: str) -> str:
    valor = os.getenv(nome, "").strip()
    if not valor:
        raise SystemExit(
            f"Variavel {nome} nao definida em REDIS/.env — copie de "
            "REDIS/.env.example e preencha."
        )
    return valor


def anthropic_api_key() -> str:
    return _obrigatoria("ANTHROPIC_API_KEY")


def claude_model() -> str:
    return os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")


def telegram_bot_token() -> str:
    return _obrigatoria("TELEGRAM_BOT_TOKEN")


def telegram_authorized_chat_ids() -> set[str]:
    bruto = os.getenv("TELEGRAM_AUTHORIZED_CHAT_IDS", "").strip()
    return {c.strip() for c in bruto.split(",") if c.strip()}
