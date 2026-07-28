# Núcleo v2 — Canal real via Telegram Bot API — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementar `Canal` (Plano 2) de verdade sobre a API do
Telegram — envio (`sendMessage`) e recebimento (`getUpdates`, long
poll) — como peça final de infra antes do `main.py` de assembly (plano
seguinte, mais smoke-test que unidade).

**Architecture:** `CanalTelegram(token)` implementa `.enviar()` (parte
do Protocol `Canal` do Plano 2) e `.receber_atualizacoes()` (usado
pelo loop externo, fora do Protocol). Preserva a correção de rede já
validada em produção em `AGENTES/julio/telegram_transport.py`: força
IPv4 (a rota IPv6 até `api.telegram.org` é instável neste ambiente —
medido: ~50% das chamadas de `sendMessage` travavam por handshake TLS
via IPv6) e retry (3 tentativas, 1.5s entre elas) — não é "legado pra
descartar", é uma correção de ambiente com causa raiz documentada.

**Tech Stack:** Python 3.11+, `requests`, `pytest` (`unittest.mock`).

## Global Constraints

- Não mexe em `AGENTES/julio/`, `TOOLS/`, `LEGADO/`.
- Testes mockam `requests.post` — nunca fazem chamada de rede real,
  nunca precisam de token de bot de verdade.
- Token é injetado no construtor — este módulo nunca lê `.env` sozinho
  (quem monta o `main.py` decide de onde vem o token).

---

## File Structure

- Create: `ARQUITETURA/nucleo/canal_telegram.py`
- Create: `ARQUITETURA/nucleo/tests/test_canal_telegram.py`

---

### Task 1: `CanalTelegram` — envio e recebimento via Bot API

**Files:**
- Create: `ARQUITETURA/nucleo/canal_telegram.py`
- Test: `ARQUITETURA/nucleo/tests/test_canal_telegram.py`

**Interfaces:**
- Produces:
  - `class CanalTelegram(token: str)` — implementa o Protocol `Canal`
    (`ARQUITETURA.nucleo.agente`).
  - `.enviar(destinatario: str, texto: str) -> None` — quebra texto em
    pedaços de até 4000 chars (limite prático do Telegram), um
    `sendMessage` por pedaço.
  - `.receber_atualizacoes(offset: int | None, timeout: int = 30) -> list[dict]` —
    `getUpdates` com long poll; inclui `offset` no payload só quando
    não for `None`; devolve `resposta["result"]` (lista vazia se
    ausente).
  - Toda chamada HTTP: até 3 tentativas com 1.5s de espera entre elas
    em caso de `requests.RequestException`; levanta a última exceção
    se todas falharem.

- [x] **Step 1: Write the failing tests**

```python
# ARQUITETURA/nucleo/tests/test_canal_telegram.py
from unittest.mock import MagicMock, patch

import pytest
import requests

from ARQUITETURA.nucleo.canal_telegram import CanalTelegram


def _resposta_ok(corpo: dict) -> MagicMock:
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = corpo
    return resp


def test_enviar_faz_post_com_chat_id_e_texto():
    canal = CanalTelegram(token="ABC123")
    with patch("ARQUITETURA.nucleo.canal_telegram.requests.post") as post_mock:
        post_mock.return_value = _resposta_ok({"ok": True})
        canal.enviar("chat1", "ola mundo")

    assert post_mock.call_count == 1
    url_chamada, kwargs = post_mock.call_args[0][0], post_mock.call_args[1]
    assert "ABC123" in url_chamada
    assert "sendMessage" in url_chamada
    assert kwargs["json"] == {"chat_id": "chat1", "text": "ola mundo"}


def test_enviar_quebra_texto_longo_em_pedacos_de_4000():
    canal = CanalTelegram(token="ABC123")
    texto_longo = "x" * 8500
    with patch("ARQUITETURA.nucleo.canal_telegram.requests.post") as post_mock:
        post_mock.return_value = _resposta_ok({"ok": True})
        canal.enviar("chat1", texto_longo)

    assert post_mock.call_count == 3
    tamanhos = [len(chamada.kwargs["json"]["text"]) for chamada in post_mock.call_args_list]
    assert tamanhos == [4000, 4000, 500]


def test_receber_atualizacoes_sem_offset_nao_manda_o_campo():
    canal = CanalTelegram(token="ABC123")
    with patch("ARQUITETURA.nucleo.canal_telegram.requests.post") as post_mock:
        post_mock.return_value = _resposta_ok({"result": [{"update_id": 1}]})
        resultado = canal.receber_atualizacoes(offset=None)

    assert resultado == [{"update_id": 1}]
    payload = post_mock.call_args[1]["json"]
    assert "offset" not in payload


def test_receber_atualizacoes_com_offset_manda_o_campo():
    canal = CanalTelegram(token="ABC123")
    with patch("ARQUITETURA.nucleo.canal_telegram.requests.post") as post_mock:
        post_mock.return_value = _resposta_ok({"result": []})
        canal.receber_atualizacoes(offset=42)

    payload = post_mock.call_args[1]["json"]
    assert payload["offset"] == 42


def test_chamada_tenta_de_novo_apos_falha_e_depois_funciona():
    canal = CanalTelegram(token="ABC123")
    with patch("ARQUITETURA.nucleo.canal_telegram.requests.post") as post_mock, \
         patch("ARQUITETURA.nucleo.canal_telegram.time.sleep") as sleep_mock:
        post_mock.side_effect = [
            requests.exceptions.ConnectionError("falhou"),
            _resposta_ok({"ok": True}),
        ]
        canal.enviar("chat1", "oi")

    assert post_mock.call_count == 2
    assert sleep_mock.call_count == 1


def test_chamada_levanta_apos_esgotar_tentativas():
    canal = CanalTelegram(token="ABC123")
    with patch("ARQUITETURA.nucleo.canal_telegram.requests.post") as post_mock, \
         patch("ARQUITETURA.nucleo.canal_telegram.time.sleep"):
        post_mock.side_effect = requests.exceptions.ConnectionError("falhou sempre")
        with pytest.raises(requests.exceptions.ConnectionError):
            canal.enviar("chat1", "oi")

    assert post_mock.call_count == 3
```

- [x] **Step 2: Run tests to verify they fail**

Run: `pytest ARQUITETURA/nucleo/tests/test_canal_telegram.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ARQUITETURA.nucleo.canal_telegram'`

- [x] **Step 3: Write minimal implementation**

```python
# ARQUITETURA/nucleo/canal_telegram.py
"""Canal real via Telegram Bot API -- implementa o Protocol Canal
(ARQUITETURA.nucleo.agente) usando long-polling + envio. A rota IPv6
ate api.telegram.org e instavel neste ambiente (medido em producao,
AGENTES/julio/telegram_transport.py: ~50% das chamadas de sendMessage
travavam no handshake TLS por IPv6, 4/4 tentativas forcando IPv4
respondiam em ~1s) -- por isso forcamos IPv4 pra qualquer chamada
deste modulo. Retry tambem preservado: uma falha de rede aqui nao pode
simplesmente engolir a mensagem do usuario.
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
```

- [x] **Step 4: Run tests to verify they pass**

Run: `pytest ARQUITETURA/nucleo/tests/test_canal_telegram.py -v`
Expected: PASS (6 tests)

- [x] **Step 5: Commit**

```bash
git add ARQUITETURA/nucleo/canal_telegram.py ARQUITETURA/nucleo/tests/test_canal_telegram.py
git commit -m "feat: CanalTelegram - Canal real via Bot API, IPv4 forcado + retry (nucleo v2)"
```

---

## Depois deste plano

Falta só o `main.py` de assembly: liga `CanalTelegram` (token real de
`REDIS/.env`) + `RepositorioEstadoRedis` (cliente Redis real) +
`criar_executor_tool` (com `discover_tool.catalogar_tools()` real) +
`DespachanteConcorrente` + `anthropic.Anthropic()` real. Isso é
integração/smoke-test, não unidade pura — só faz sentido escrever E
RODAR numa sessão em que o usuário confirme que quer testar contra o
Telegram de verdade (evita rodar dois consumidores do mesmo token
simultaneamente, ou mandar mensagem indesejada a um chat real).
