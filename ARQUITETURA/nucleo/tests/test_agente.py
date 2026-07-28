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


def test_estado_conversa_plano_aprovado_default_false():
    estado = EstadoConversa()
    assert estado.plano_aprovado is False


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


from ARQUITETURA.nucleo.agente import resolver_pendencia

PENDENTE_EXEMPLO = {"tool_use_id": "toolu_1", "name": "criar_campanha", "input": {"nome": "X"}}


def test_resolver_pendencia_nao_confirma_cancela():
    canal = CanalFake()
    estado = EstadoConversa(historico=[{"role": "user", "content": "oi"}], pendente=PENDENTE_EXEMPLO)
    resolver_pendencia(
        ClienteAnthropicFake(respostas=[]), "modelo-x", "sistema", [], estado,
        confirmou=False, executar_tool=lambda n, e: {}, destinatario="chat1", canal=canal,
    )
    assert estado.pendente is None
    assert estado.historico == []
    assert estado.plano_aprovado is False
    assert "cancel" in canal.enviados[0][1].lower()


def test_resolver_pendencia_confirma_sucesso_e_continua_o_loop():
    canal = CanalFake()
    estado = EstadoConversa(pendente=PENDENTE_EXEMPLO)
    cliente = ClienteAnthropicFake(respostas=[fake_response(fake_text("prontinho, tudo certo"))])
    resolver_pendencia(
        cliente, "modelo-x", "sistema", [TOOL_SIMPLES], estado,
        confirmou=True, executar_tool=lambda n, e: {"ok": True}, destinatario="chat1", canal=canal,
    )
    assert estado.pendente is None
    assert estado.plano_aprovado is False
    assert any("prontinho" in msg for _, msg in canal.enviados)


def test_resolver_pendencia_falha_permanente_cancela_e_explica():
    canal = CanalFake()
    estado = EstadoConversa(pendente=PENDENTE_EXEMPLO)

    def executar(nome, entrada):
        raise FalhaPermanente("titulo excede 30 caracteres")

    resolver_pendencia(
        ClienteAnthropicFake(respostas=[]), "modelo-x", "sistema", [], estado,
        confirmou=True, executar_tool=executar, destinatario="chat1", canal=canal,
    )
    assert estado.pendente is None
    assert estado.plano_aprovado is False
    assert "titulo excede 30 caracteres" in canal.enviados[0][1]


def test_resolver_pendencia_falha_transitoria_preserva_pendencia():
    canal = CanalFake()
    estado = EstadoConversa(pendente=dict(PENDENTE_EXEMPLO))

    def executar(nome, entrada):
        raise FalhaTransitoria("ModuleNotFoundError: no module google")

    resolver_pendencia(
        ClienteAnthropicFake(respostas=[]), "modelo-x", "sistema", [], estado,
        confirmou=True, executar_tool=executar, destinatario="chat1", canal=canal,
    )
    assert estado.pendente == PENDENTE_EXEMPLO
    assert estado.plano_aprovado is False


TOOL_CONFIRMACAO_SIMPLES = {
    "name": "criar_campanha",
    "description": "cria recurso generico",
    "requer_confirmacao": True,
    "input_schema": {
        "type": "object",
        "properties": {"nome": {"type": "string"}},
        "required": ["nome"],
    },
}


def test_plano_aprovado_permite_tool_requer_confirmacao_direto_sem_pendencia():
    """Confirma o 1o passo (orcamento); o agente decide criar a
    campanha em seguida (2o passo, MESMA tool requer_confirmacao) --
    com plano_aprovado=True, executa direto, sem pedir confirmacao de
    novo."""
    cliente = ClienteAnthropicFake(respostas=[
        fake_response(fake_tool_use(id="toolu_1", name="criar_campanha", input={"nome": "orcamento"})),
    ])
    canal = CanalFake()
    estado = EstadoConversa()
    chamadas = []

    def executar(nome, entrada):
        chamadas.append(entrada)
        return {"ok": True, "resource_name": f"recurso/{len(chamadas)}"}

    processar_turno(
        cliente, "modelo-x", "sistema", [TOOL_CONFIRMACAO_SIMPLES], estado, "cria a campanha completa",
        executar_tool=executar, destinatario="chat1", canal=canal,
    )
    assert estado.pendente is not None
    assert estado.plano_aprovado is False

    cliente_confirmacao = ClienteAnthropicFake(respostas=[
        fake_response(fake_tool_use(id="toolu_2", name="criar_campanha", input={"nome": "campanha real"})),
        fake_response(fake_text("prontinho, plano concluido")),
    ])
    resolver_pendencia(
        cliente_confirmacao, "modelo-x", "sistema", [TOOL_CONFIRMACAO_SIMPLES], estado,
        confirmou=True, executar_tool=executar, destinatario="chat1", canal=canal,
    )

    assert len(chamadas) == 2
    assert estado.pendente is None
    assert estado.plano_aprovado is False
    assert any("prontinho" in msg for _, msg in canal.enviados)
    assert "ModuleNotFoundError" not in canal.enviados[0][1]
