import json

from ARQUITETURA.nucleo.agente import EstadoConversa
from ARQUITETURA.nucleo.memoria import RepositorioEstadoMemoria, RepositorioEstadoRedis


class ClienteRedisFake:
    """So os 2 metodos que RepositorioEstadoRedis usa -- sem rede."""

    def __init__(self):
        self._dados: dict[str, str] = {}

    def get(self, chave: str) -> str | None:
        return self._dados.get(chave)

    def set(self, chave: str, valor: str) -> None:
        self._dados[chave] = valor


def test_repositorio_memoria_devolve_estado_vazio_pra_chat_novo():
    repo = RepositorioEstadoMemoria()
    estado = repo.carregar("chat_novo")
    assert estado.historico == []
    assert estado.pendente is None


def test_repositorio_redis_persiste_plano_aprovado():
    cliente = ClienteRedisFake()
    repo = RepositorioEstadoRedis(cliente)
    estado = EstadoConversa(plano_aprovado=True)
    repo.salvar("chat1", estado)
    recarregado = repo.carregar("chat1")
    assert recarregado.plano_aprovado is True


def test_repositorio_memoria_salva_e_recarrega():
    repo = RepositorioEstadoMemoria()
    estado = EstadoConversa(historico=[{"role": "user", "content": "oi"}], pendente={"x": 1})
    repo.salvar("chat1", estado)
    recarregado = repo.carregar("chat1")
    assert recarregado.historico == [{"role": "user", "content": "oi"}]
    assert recarregado.pendente == {"x": 1}


def test_repositorio_redis_devolve_estado_vazio_pra_chave_ausente():
    repo = RepositorioEstadoRedis(ClienteRedisFake())
    estado = repo.carregar("chat_novo")
    assert estado.historico == []
    assert estado.pendente is None


def test_repositorio_redis_salva_e_recarrega_via_json():
    cliente = ClienteRedisFake()
    repo = RepositorioEstadoRedis(cliente)
    estado = EstadoConversa(historico=[{"role": "user", "content": "oi"}], pendente={"x": 1})
    repo.salvar("chat1", estado)

    # confirma que foi serializado como JSON de verdade na chave certa
    bruto = cliente.get("estado:chat1")
    assert json.loads(bruto) == {
        "historico": [{"role": "user", "content": "oi"}], "pendente": {"x": 1}, "plano_aprovado": False,
    }

    recarregado = repo.carregar("chat1")
    assert recarregado.historico == estado.historico
    assert recarregado.pendente == estado.pendente


def test_repositorio_redis_usa_prefixo_customizado():
    cliente = ClienteRedisFake()
    repo = RepositorioEstadoRedis(cliente, prefixo="outro:")
    repo.salvar("chat1", EstadoConversa())
    assert "outro:chat1" in cliente._dados


from ARQUITETURA.nucleo.memoria import (
    carregar_resumo,
    montar_system_com_resumo,
    salvar_resumo,
)


def test_carregar_resumo_none_quando_nunca_salvo():
    cliente = ClienteRedisFake()
    assert carregar_resumo(cliente, "chat1") is None


def test_salvar_e_carregar_resumo():
    cliente = ClienteRedisFake()
    salvar_resumo(cliente, "chat1", "cliente pediu campanha pro patinho cubo")
    assert carregar_resumo(cliente, "chat1") == "cliente pediu campanha pro patinho cubo"


def test_montar_system_sem_resumo_devolve_base_intacto():
    assert montar_system_com_resumo("Voce e o Julio.", None) == "Voce e o Julio."
    assert montar_system_com_resumo("Voce e o Julio.", "") == "Voce e o Julio."


def test_montar_system_com_resumo_anexa_secao():
    resultado = montar_system_com_resumo("Voce e o Julio.", "pendente: confirmar campanha X")
    assert "Voce e o Julio." in resultado
    assert "pendente: confirmar campanha X" in resultado
    assert resultado.index("Voce e o Julio.") < resultado.index("pendente: confirmar campanha X")
