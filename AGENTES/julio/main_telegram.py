"""Bot conversacional (Telegram) -- um agente so (Julio, orchestrator.py),
cobrindo marketing de site E desenvolvimento do proprio projeto (ver
commit da fusao Julio+Elis, 2026-07-27). Antes eram 2 agentes alternados
por AGENTE_ATIVO; isso nao existe mais.

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

    processar_mensagem = orchestrator.processar_mensagem

    print(f"Chat_ids autorizados: {autorizados}")
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
                # Log tecnico completo so no console/arquivo -- nunca mostrar exececao
                # crua (tipo/traceback Python) pro usuario de negocio no Telegram. Isso
                # ja confundiu o LLM em conversas seguintes (viu "ModuleNotFoundError"
                # e tentou "consertar o projeto" em vez de so tentar de novo).
                print(f"Erro processando mensagem de {chat_id}: {exc}")
                try:
                    telegram_transport.enviar(
                        chat_id,
                        "Deu um erro tecnico aqui do meu lado processando sua mensagem -- "
                        "ja registrei pra investigar. Pode tentar de novo?",
                    )
                except requests.RequestException:
                    pass


if __name__ == "__main__":
    sys.exit(rodar_loop())
