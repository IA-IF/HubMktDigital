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
