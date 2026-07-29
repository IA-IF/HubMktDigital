"""Envia uma mensagem pro grupo telegram_v2 e loga como "ia" em
BOTV2/logs/conversa.md. E assim que eu (Claude) respondo -- o bot em si
(BOTV2/escutar.py) nunca decide/gera resposta sozinho.

Uso:
    python -m BOTV2.enviar "texto da resposta"
"""
import sys

from BOTV2.canal import enviar as enviar_telegram
from BOTV2.config import carregar, carregar_grupo_chat_id
from BOTV2.log import registrar


def enviar(texto: str) -> None:
    token, _ = carregar()
    chat_id = carregar_grupo_chat_id()
    enviar_telegram(token, chat_id, texto)
    registrar("ia", texto)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit('Uso: python -m BOTV2.enviar "texto"')
    enviar(sys.argv[1])
