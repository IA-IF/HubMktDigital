"""Config do Julio (parte conversacional: Telegram, selecao de site, tools).

Nome do modulo deliberadamente diferente de "config" — esse nome ja e
usado por REDIS/llm_router/config.py, e o cache de modulos do Python e
por nome (nao por caminho); ter dois arquivos chamados "config.py" no
mesmo processo faria um pisar no outro dependendo da ordem de import.

Credenciais compartilhadas (Anthropic, Telegram) vem de REDIS/.env, mesmo
arquivo que o llm_router ja usa — nao duplicado, so carregado de novo aqui
(load_dotenv de novo no mesmo arquivo e inofensivo).
"""
import os
import subprocess
from pathlib import Path

from dotenv import load_dotenv

PACKAGE_ROOT = Path(__file__).resolve().parent
HUB_ROOT = PACKAGE_ROOT.parent.parent
ENV_FILE = HUB_ROOT / "REDIS" / ".env"
load_dotenv(ENV_FILE)

DATA_DIR = PACKAGE_ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Backlog de pedidos que nenhuma tool ainda resolve (ver pedidos.py).
PEDIDOS_FUTUROS = DATA_DIR / "pedidos-futuros.md"

# Nome bonito pra exibir de volta pro humano (slug -> nome).
SITE_NOMES = {
    "integrafoods": "Integra Foods",
    "3gfoods": "3G Foods",
    "adoro": "Adoro",
}


def global_md() -> Path:
    """Personalidade/comportamento do Julio, valido em qualquer site —
    ver AGENTES/julio/GLOBAL.md."""
    return PACKAGE_ROOT / "GLOBAL.md"


def global_md_default() -> Path:
    """Copia da secao 'Personalidade / comportamento' original, salva pra
    /fix_julio_default poder restaurar depois de qualquer ajuste feito
    via /fix_julio."""
    return PACKAGE_ROOT / "GLOBAL.default.md"


def status_projeto_md() -> Path:
    """Contexto fixo da Elis -- ver AGENTES/julio/STATUS_PROJETO.md."""
    return PACKAGE_ROOT / "STATUS_PROJETO.md"


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


def status_token() -> str:
    """Token do endpoint HTTP de start/stop/status na EC2 (status_server.py)
    -- ver plano docs/superpowers/plans/2026-07-27-status-controle-bot-ec2.md."""
    return _obrigatoria("STATUS_TOKEN")


def status_server_port() -> int:
    return int(os.getenv("STATUS_SERVER_PORT", "8765"))


def ambiente() -> str:
    """"EC2" ou "local" -- setado manualmente em REDIS/.env de cada
    maquina (default "local"), pra separar qual instancia esta
    respondendo no Telegram."""
    return os.getenv("AMBIENTE", "local").strip()


def texto_status() -> str:
    """Versao (hash curto do commit atual) + ambiente, pro comando
    /status do bot -- calculado na hora, nada gravado em deploy."""
    resultado = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"], cwd=HUB_ROOT,
        capture_output=True, text=True,
    )
    versao = resultado.stdout.strip() if resultado.returncode == 0 else "desconhecida"
    return f"Versao: {versao}\nAmbiente: {ambiente()}"
