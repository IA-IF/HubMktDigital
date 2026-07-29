"""Cliente minimo da Telegram Bot API pro telegram_v2 -- so enviar/receber,
sem nenhuma dependencia de ARQUITETURA/ ou AGENTES/julio. Forca IPv4 (mesmo
motivo do ARQUITETURA/nucleo/canal_telegram.py: rota IPv6 instavel nesse
ambiente).
"""
import socket

import requests
import urllib3.util.connection as urllib3_conexao

API_BASE = "https://api.telegram.org/bot{token}/{metodo}"

urllib3_conexao.allowed_gai_family = lambda: socket.AF_INET


def _chamar(token: str, metodo: str, **params) -> dict:
    url = API_BASE.format(token=token, metodo=metodo)
    timeout_http = params.get("timeout", 0) + 10 if metodo == "getUpdates" else 15
    resp = requests.post(url, json=params, timeout=timeout_http)
    resp.raise_for_status()
    return resp.json()


def enviar(token: str, chat_id: str, texto: str) -> None:
    for i in range(0, len(texto), 4000):
        _chamar(token, "sendMessage", chat_id=chat_id, text=texto[i:i + 4000])


def receber_atualizacoes(token: str, offset: int | None, timeout: int = 30) -> list[dict]:
    params = {"timeout": timeout}
    if offset is not None:
        params["offset"] = offset
    resposta = _chamar(token, "getUpdates", **params)
    return resposta.get("result", [])
