"""Camada fina de transporte com a API do Telegram (long polling + envio).

Portado de LEGADO/agente-julio/src/telegram_transport.py (2026-07-22) —
mesma logica, sem mudanca. Separado do resto de proposito: o dia que o
agente ganhar outro canal (WhatsApp, Slack, etc.), so este arquivo muda.

A rota IPv6 ate api.telegram.org neste ambiente e instavel (medido: ~50%
das chamadas de sendMessage travavam no handshake TLS e davam ReadTimeout
por IPv6, enquanto 4/4 tentativas forcando IPv4 respondiam em ~1s) — por
isso forcamos IPv4 pra qualquer chamada deste modulo. Mantemos tambem
retry: mesmo IPv4 nao e garantia de rede perfeita, e uma falha aqui nao
pode simplesmente engolir a mensagem do usuario.
"""
import socket
import time

import requests
import urllib3.util.connection as urllib3_conexao

import julio_config as config

API_BASE = "https://api.telegram.org/bot{token}/{metodo}"
TENTATIVAS = 3

urllib3_conexao.allowed_gai_family = lambda: socket.AF_INET


def _telegram(metodo: str, **params) -> dict:
    token = config.telegram_bot_token()
    url = API_BASE.format(token=token, metodo=metodo)
    # getUpdates faz long poll (fica esperando no servidor ate `timeout`
    # segundos) — o timeout do lado do cliente precisa ser maior que isso.
    # Os demais metodos (sendMessage etc.) sao rapidos; timeout curto so
    # pra nao ficar 35s preso numa chamada que devia levar 1s.
    timeout_http = params.get("timeout", 0) + 10 if metodo == "getUpdates" else 15

    ultimo_erro: Exception | None = None
    for tentativa in range(TENTATIVAS):
        try:
            resp = requests.post(url, json=params, timeout=timeout_http)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as exc:
            ultimo_erro = exc
            if tentativa < TENTATIVAS - 1:
                time.sleep(1.5)
    raise ultimo_erro


def enviar(chat_id: str, texto: str) -> None:
    for i in range(0, len(texto), 4000):
        _telegram("sendMessage", chat_id=chat_id, text=texto[i:i + 4000])


def receber_atualizacoes(offset: int | None, timeout: int = 30) -> list[dict]:
    params = {"timeout": timeout}
    if offset is not None:
        params["offset"] = offset
    resposta = _telegram("getUpdates", **params)
    return resposta.get("result", [])
