"""Bot conversacional (Telegram) que roda UM dos dois agentes de conversa
do projeto -- Julio (marketing de site, orchestrator.py) ou Elis
(desenvolvimento do proprio projeto, elis_orchestrator.py) -- escolhido
por AGENTE_ATIVO em REDIS/.env (ver julio_config.agente_ativo()).

Roda como processo continuo (long polling no Telegram), UM SO PROCESSO.
So chat_ids na whitelist (TELEGRAM_AUTHORIZED_CHAT_IDS em REDIS/.env)
podem falar com ele.

Nome do arquivo (main_telegram.py, nao main.py): este pacote ja tem um
main.py (o CLI de teste do ConversationalAgent puro, sem tools/Telegram) —
mantido a parte pra nao perder aquele fluxo simples de teste.

Uso:
    python main_telegram.py
"""
import sys
import time

import requests

import elis_orchestrator
import julio_config as config
import orchestrator
import telegram_transport


def rodar_loop() -> None:
    autorizados = config.telegram_authorized_chat_ids()
    if not autorizados:
        raise SystemExit(
            "TELEGRAM_AUTHORIZED_CHAT_IDS vazio em REDIS/.env — defina ao "
            "menos um chat_id autorizado antes de rodar o bot."
        )

    agente = config.agente_ativo()
    processar_mensagem = orchestrator.processar_mensagem if agente == "julio" else elis_orchestrator.processar_mensagem

    print(f"Agente ativo: {agente}. Chat_ids autorizados: {autorizados}")
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
                processar_mensagem(chat_id, mensagem["text"], telegram_transport)
            except Exception as exc:  # noqa: BLE001 — nao derrubar o loop por erro de 1 msg
                print(f"Erro processando mensagem de {chat_id}: {exc}")
                try:
                    telegram_transport.enviar(chat_id, f"Erro interno: {exc}")
                except requests.RequestException:
                    pass


if __name__ == "__main__":
    sys.exit(rodar_loop())
