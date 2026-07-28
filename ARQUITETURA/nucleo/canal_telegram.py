"""Canal real via Telegram Bot API -- implementa o Protocol Canal
(ARQUITETURA.nucleo.agente) usando long-polling + envio. A rota IPv6
ate api.telegram.org e instavel neste ambiente (medido em produção,
AGENTES/julio/telegram_transport.py: ~50% das chamadas de sendMessage
travavam no handshake TLS por IPv6, 4/4 tentativas forçando IPv4
respondiam em ~1s) -- por isso forçamos IPv4 pra qualquer chamada
deste módulo. Retry também preservado: uma falha de rede aqui não pode
simplesmente engolir a mensagem do usuário.
"""
import socket
import time

import requests
import urllib3.util.connection as urllib3_conexao

API_BASE = "https://api.telegram.org/bot{token}/{metodo}"
TENTATIVAS = 3

urllib3_conexao.allowed_gai_family = lambda: socket.AF_INET


class CanalTelegram:
    def __init__(self, token: str) -> None:
        self._token = token

    def _chamar(self, metodo: str, **params) -> dict:
        url = API_BASE.format(token=self._token, metodo=metodo)
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

    def enviar(self, destinatario: str, texto: str) -> None:
        for i in range(0, len(texto), 4000):
            self._chamar("sendMessage", chat_id=destinatario, text=texto[i:i + 4000])

    def receber_atualizacoes(self, offset: int | None, timeout: int = 30) -> list[dict]:
        params = {"timeout": timeout}
        if offset is not None:
            params["offset"] = offset
        resposta = self._chamar("getUpdates", **params)
        return resposta.get("result", [])
