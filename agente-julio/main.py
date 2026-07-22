"""Julio — bot conversacional que aciona os outros agentes (hoje: agente-ads).

Roda como processo continuo (long polling no Telegram). So chat_ids na
whitelist (TELEGRAM_AUTHORIZED_CHAT_IDS no .env.<SITE>) podem falar com ele.

Uso:
    SITE=<site> python main.py
"""
import sys
import time

import requests

from src import config, orchestrator, telegram_transport


def rodar_loop() -> None:
    autorizados = config.telegram_authorized_chat_ids()
    if not autorizados:
        raise SystemExit(
            f"TELEGRAM_AUTHORIZED_CHAT_IDS vazio em .env.{config.SITE} — defina "
            "ao menos um chat_id autorizado antes de rodar o bot."
        )

    print(f"Julio rodando para o site '{config.SITE}'. Chat_ids autorizados: {autorizados}")
    offset = None
    while True:
        try:
            atualizacoes = telegram_transport.receber_atualizacoes(offset)
        except requests.RequestException as exc:
            print(f"Erro de rede, tentando de novo em 5s: {exc}")
            time.sleep(5)
            continue

        for update in atualizacoes:
            offset = update["update_id"] + 1
            mensagem = update.get("message")
            if not mensagem or "text" not in mensagem:
                continue
            chat_id = str(mensagem["chat"]["id"])
            if chat_id not in autorizados:
                telegram_transport.enviar(chat_id, "Voce nao esta autorizado a usar este bot.")
                continue
            try:
                orchestrator.processar_mensagem(chat_id, mensagem["text"], config.SITE)
            except Exception as exc:  # noqa: BLE001 — nao derrubar o loop por erro de 1 msg
                print(f"Erro processando mensagem de {chat_id}: {exc}")
                try:
                    telegram_transport.enviar(chat_id, f"Erro interno: {exc}")
                except requests.RequestException:
                    pass


if __name__ == "__main__":
    sys.exit(rodar_loop())
