from ARQUITETURA.nucleo.agente import CanalFake
from ARQUITETURA.nucleo.main import processar_mensagem
from ARQUITETURA.nucleo.memoria import RepositorioEstadoMemoria


class ClienteAnthropicNuncaChamado:
    """Prova que /status nao gasta token: qualquer chamada aqui e um bug."""

    class _Mensagens:
        def create(self, **kwargs):
            raise AssertionError("/status nao deveria chamar a API da Anthropic")

    def __init__(self):
        self.messages = self._Mensagens()


class ClienteRedisFake:
    def __init__(self):
        self._dados: dict[str, str] = {}

    def get(self, chave: str) -> str | None:
        return self._dados.get(chave)

    def set(self, chave: str, valor: str) -> None:
        self._dados[chave] = valor

    def hgetall(self, chave: str) -> dict:
        return {}


def test_status_nao_chama_anthropic_nem_le_estado_da_conversa():
    canal = CanalFake()
    repositorio = RepositorioEstadoMemoria()
    cliente_redis = ClienteRedisFake()

    processar_mensagem(
        "chat1", "/status", cliente_redis, repositorio, ClienteAnthropicNuncaChamado(),
        tool_por_nome={}, canal=canal, modelo="modelo-qualquer",
    )

    assert len(canal.enviados) == 1
    destinatario, texto = canal.enviados[0]
    assert destinatario == "chat1"
    assert "Versao:" in texto
    assert "Arquitetura: nucleo v2" in texto
    # nao deve ter criado/alterado estado de conversa pra este chat
    assert repositorio.carregar("chat1").historico == []


def test_status_e_case_insensitive_e_ignora_espacos():
    canal = CanalFake()
    repositorio = RepositorioEstadoMemoria()

    processar_mensagem(
        "chat1", "  /STATUS  ", ClienteRedisFake(), repositorio, ClienteAnthropicNuncaChamado(),
        tool_por_nome={}, canal=canal, modelo="modelo-qualquer",
    )

    assert len(canal.enviados) == 1
