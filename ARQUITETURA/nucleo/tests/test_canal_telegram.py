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
