import pytest

from ARQUITETURA.nucleo.fake_anthropic import (
    ClienteAnthropicFake,
    fake_response,
    fake_text,
    fake_tool_use,
)


def test_fake_tool_use_tem_forma_de_bloco_real():
    bloco = fake_tool_use(id="toolu_1", name="minha_tool", input={"x": 1})
    assert bloco.type == "tool_use"
    assert bloco.id == "toolu_1"
    assert bloco.name == "minha_tool"
    assert bloco.input == {"x": 1}
    assert bloco.model_dump()["type"] == "tool_use"


def test_fake_text_tem_forma_de_bloco_real():
    bloco = fake_text("ola")
    assert bloco.type == "text"
    assert bloco.text == "ola"


def test_cliente_fake_devolve_respostas_na_ordem():
    cliente = ClienteAnthropicFake(respostas=[
        fake_response(fake_text("primeira")),
        fake_response(fake_text("segunda")),
    ])
    r1 = cliente.messages.create(messages=[{"role": "user", "content": "oi"}])
    r2 = cliente.messages.create(messages=[{"role": "user", "content": "oi de novo"}])
    assert r1.content[0].text == "primeira"
    assert r2.content[0].text == "segunda"


def test_cliente_fake_levanta_quando_fila_esgota():
    cliente = ClienteAnthropicFake(respostas=[fake_response(fake_text("unica"))])
    cliente.messages.create(messages=[])
    with pytest.raises(IndexError):
        cliente.messages.create(messages=[])


def test_cliente_fake_aceita_historico_bem_formado():
    cliente = ClienteAnthropicFake(respostas=[fake_response(fake_text("ok"))])
    mensagens = [
        {"role": "user", "content": "oi"},
        {"role": "assistant", "content": [
            {"type": "tool_use", "id": "toolu_1", "name": "t", "input": {}},
        ]},
        {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "toolu_1", "content": "ok"},
        ]},
    ]
    cliente.messages.create(messages=mensagens)  # nao deve levantar


def test_cliente_fake_pega_tool_use_paralelo_sem_par():
    """Reproduz o bug real: 2 tool_use no mesmo turno, so 1 tool_result
    pareado -- exatamente o que quebrou em producao (AGENTES/julio/
    orchestrator.py, ver plano de correcao 2026-07-27)."""
    cliente = ClienteAnthropicFake(respostas=[fake_response(fake_text("ok"))])
    mensagens = [
        {"role": "user", "content": "oi"},
        {"role": "assistant", "content": [
            {"type": "tool_use", "id": "toolu_1", "name": "t", "input": {}},
            {"type": "tool_use", "id": "toolu_2", "name": "t", "input": {}},
        ]},
        {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "toolu_1", "content": "ok"},
        ]},
    ]
    with pytest.raises(AssertionError, match="toolu_2"):
        cliente.messages.create(messages=mensagens)


def test_cliente_fake_pega_tool_result_duplicado():
    """Reproduz o bug real do plano_aprovado: resolver_pendencia
    anexava um 2o tool_result pro MESMO tool_use_id que ja tinha um
    placeholder -- a API real rejeita com 'each tool_use must have a
    single result' (achado ao vivo, 2026-07-27)."""
    cliente = ClienteAnthropicFake(respostas=[fake_response(fake_text("ok"))])
    mensagens = [
        {"role": "user", "content": "oi"},
        {"role": "assistant", "content": [
            {"type": "tool_use", "id": "toolu_1", "name": "t", "input": {}},
        ]},
        {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "toolu_1", "content": "aguardando confirmacao"},
            {"type": "tool_result", "tool_use_id": "toolu_1", "content": "resultado real"},
        ]},
    ]
    with pytest.raises(AssertionError, match="toolu_1"):
        cliente.messages.create(messages=mensagens)
