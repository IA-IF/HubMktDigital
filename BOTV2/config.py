"""Configuracao do telegram_v2 -- token/allowlist vem de REDIS/.env (mesmo
arquivo gitignored do resto do projeto, so lido de novo aqui).

O bot roda dentro de um GRUPO (Eduardo + Leandro + bot) -- chat_id do grupo
e o mesmo pra todo mundo, entao autorizacao e feita pelo id de quem enviou
(`message.from.id`), nao pelo chat_id. GRUPO_CHAT_ID_FILE guarda o chat_id
do grupo assim que a primeira mensagem chega, pra `enviar.py` saber pra
onde mandar sem precisar passar o id toda vez."""
from pathlib import Path

from dotenv import dotenv_values

RAIZ = Path(__file__).resolve().parents[1]
ENV_FILE = RAIZ / "REDIS" / ".env"
LOG_FILE = Path(__file__).resolve().parent / "logs" / "conversa.md"
GRUPO_CHAT_ID_FILE = Path(__file__).resolve().parent / "logs" / "grupo_chat_id.txt"

NOMES_POR_USUARIO_ID = {
    "8297590261": "eduardo",
    "8800634507": "leandro",
}


def salvar_grupo_chat_id(chat_id: str) -> None:
    GRUPO_CHAT_ID_FILE.parent.mkdir(parents=True, exist_ok=True)
    GRUPO_CHAT_ID_FILE.write_text(chat_id, encoding="utf-8")


def carregar_grupo_chat_id() -> str:
    if not GRUPO_CHAT_ID_FILE.exists():
        raise SystemExit(
            "Ainda nao sei o chat_id do grupo -- peca pro Eduardo ou Leandro "
            "mandarem uma mensagem no grupo com o escutar.py rodando primeiro."
        )
    return GRUPO_CHAT_ID_FILE.read_text(encoding="utf-8").strip()


def carregar() -> tuple[str, set[str]]:
    env = dotenv_values(ENV_FILE)
    token = env.get("TELEGRAM_V2_BOT_TOKEN")
    if not token:
        raise SystemExit(f"TELEGRAM_V2_BOT_TOKEN nao definido em {ENV_FILE}")
    autorizados = {c.strip() for c in env.get("TELEGRAM_V2_AUTHORIZED_CHAT_IDS", "").split(",") if c.strip()}
    if not autorizados:
        raise SystemExit(f"TELEGRAM_V2_AUTHORIZED_CHAT_IDS vazio em {ENV_FILE}")
    return token, autorizados
