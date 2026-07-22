"""Camada fina de transporte com a API do Telegram (long polling + envio).

Separado do resto do orchestrator.py de proposito: o dia que o Julio ganhar
outro canal (WhatsApp, Slack, etc.), so esse arquivo muda — o resto (loop de
conversa, chamada aos outros agentes) e agnostico de canal.
"""
import requests

from src import config

API_BASE = "https://api.telegram.org/bot{token}/{metodo}"


def _telegram(metodo: str, **params) -> dict:
    token = config.telegram_bot_token()
    resp = requests.post(API_BASE.format(token=token, metodo=metodo), json=params, timeout=35)
    resp.raise_for_status()
    return resp.json()


def enviar(chat_id: str, texto: str) -> None:
    for i in range(0, len(texto), 4000):
        _telegram("sendMessage", chat_id=chat_id, text=texto[i:i + 4000])


def receber_atualizacoes(offset: int | None, timeout: int = 30) -> list[dict]:
    params = {"timeout": timeout}
    if offset is not None:
        params["offset"] = offset
    resposta = _telegram("getUpdates", **params)
    return resposta.get("result", [])
