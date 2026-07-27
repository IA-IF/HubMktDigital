from ARQUITETURA.nucleo.agente import (
    CanalFake,
    EstadoConversa,
    FalhaPermanente,
    FalhaTransitoria,
)


def test_canal_fake_registra_mensagens_enviadas():
    canal = CanalFake()
    canal.enviar("chat1", "ola")
    canal.enviar("chat1", "de novo")
    assert canal.enviados == [("chat1", "ola"), ("chat1", "de novo")]


def test_estado_conversa_default_vazio():
    estado = EstadoConversa()
    assert estado.historico == []
    assert estado.pendente is None


def test_falha_permanente_e_transitoria_sao_excecoes_distintas():
    assert issubclass(FalhaPermanente, Exception)
    assert issubclass(FalhaTransitoria, Exception)
    assert not issubclass(FalhaPermanente, FalhaTransitoria)
    assert not issubclass(FalhaTransitoria, FalhaPermanente)


from ARQUITETURA.nucleo.agente import processar_turno
from ARQUITETURA.nucleo.fake_anthropic import (
    ClienteAnthropicFake,
    fake_response,
    fake_text,
    fake_tool_use,
)

TOOL_SIMPLES = {
    "name": "somar",
    "description": "soma dois numeros",
    "input_schema": {
        "type": "object",
        "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
        "required": ["a", "b"],
    },
}

TOOL_CONFIRMACAO = {
    "name": "criar_campanha",
    "description": "cria campanha",
    "requer_confirmacao": True,
    "input_schema": {
        "type": "object",
        "properties": {
            "nome": {"type": "string"},
            "palavras_chave": {"type": "array"},
        },
        "required": ["nome", "palavras_chave"],
    },
}


def test_resposta_sem_tool_envia_texto_direto():
    cliente = ClienteAnthropicFake(respostas=[fake_response(fake_text("oi humano"))])
    canal = CanalFake()
    estado = EstadoConversa()
    processar_turno(
        cliente, "modelo-x", "sistema", [TOOL_SIMPLES], estado, "oi",
        executar_tool=lambda nome, entrada: {}, destinatario="chat1", canal=canal,
    )
    assert canal.enviados == [("chat1", "oi humano")]
    assert estado.pendente is None


def test_tool_sem_confirmacao_executa_e_continua():
    cliente = ClienteAnthropicFake(respostas=[
        fake_response(fake_tool_use(id="toolu_1", name="somar", input={"a": 2, "b": 3})),
        fake_response(fake_text("a soma deu 5")),
    ])
    canal = CanalFake()
    estado = EstadoConversa()
    chamadas = []

    def executar(nome, entrada):
        chamadas.append((nome, entrada))
        return {"resultado": entrada["a"] + entrada["b"]}

    processar_turno(
        cliente, "modelo-x", "sistema", [TOOL_SIMPLES], estado, "quanto e 2+3",
        executar_tool=executar, destinatario="chat1", canal=canal,
    )
    assert chamadas == [("somar", {"a": 2, "b": 3})]
    assert canal.enviados == [("chat1", "a soma deu 5")]
    assert estado.pendente is None


def test_tool_com_confirmacao_input_valido_cria_pendencia():
    cliente = ClienteAnthropicFake(respostas=[
        fake_response(fake_tool_use(
            id="toolu_1", name="criar_campanha",
            input={"nome": "X", "palavras_chave": ["a"]},
        )),
    ])
    canal = CanalFake()
    estado = EstadoConversa()
    processar_turno(
        cliente, "modelo-x", "sistema", [TOOL_CONFIRMACAO], estado, "cria a campanha",
        executar_tool=lambda nome, entrada: {}, destinatario="chat1", canal=canal,
    )
    assert estado.pendente == {
        "tool_use_id": "toolu_1", "name": "criar_campanha",
        "input": {"nome": "X", "palavras_chave": ["a"]},
    }
    assert len(canal.enviados) == 1
    assert "confirma" in canal.enviados[0][1].lower()


def test_tool_com_confirmacao_input_invalido_da_chance_de_corrigir():
    cliente = ClienteAnthropicFake(respostas=[
        fake_response(fake_tool_use(id="toolu_1", name="criar_campanha", input={"nome": "X"})),
        fake_response(fake_tool_use(
            id="toolu_2", name="criar_campanha",
            input={"nome": "X", "palavras_chave": ["a"]},
        )),
    ])
    canal = CanalFake()
    estado = EstadoConversa()
    processar_turno(
        cliente, "modelo-x", "sistema", [TOOL_CONFIRMACAO], estado, "cria a campanha",
        executar_tool=lambda nome, entrada: {}, destinatario="chat1", canal=canal,
    )
    # 1a tentativa invalida (faltou palavras_chave) nao virou pendencia;
    # o loop deu ao "modelo" (fake) a chance de corrigir na 2a chamada.
    assert estado.pendente == {
        "tool_use_id": "toolu_2", "name": "criar_campanha",
        "input": {"nome": "X", "palavras_chave": ["a"]},
    }


def test_tool_use_paralelo_todos_executam_e_pareiam():
    cliente = ClienteAnthropicFake(respostas=[
        fake_response(
            fake_tool_use(id="toolu_1", name="somar", input={"a": 1, "b": 1}),
            fake_tool_use(id="toolu_2", name="somar", input={"a": 2, "b": 2}),
        ),
        fake_response(fake_text("prontinho")),
    ])
    canal = CanalFake()
    estado = EstadoConversa()
    chamadas = []

    def executar(nome, entrada):
        chamadas.append(entrada)
        return {"resultado": entrada["a"] + entrada["b"]}

    processar_turno(
        cliente, "modelo-x", "sistema", [TOOL_SIMPLES], estado, "soma duas vezes",
        executar_tool=executar, destinatario="chat1", canal=canal,
    )
    assert chamadas == [{"a": 1, "b": 1}, {"a": 2, "b": 2}]
    assert canal.enviados == [("chat1", "prontinho")]
