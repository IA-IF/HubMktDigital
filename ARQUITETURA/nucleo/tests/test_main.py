from ARQUITETURA.nucleo.agente import CanalFake, EstadoConversa
from ARQUITETURA.nucleo.main import _tools_e_executor, processar_mensagem
from ARQUITETURA.nucleo.memoria import RepositorioEstadoMemoria, salvar_site


class ClienteAnthropicNuncaChamado:
    """Prova que /status e /start nao gastam token: qualquer chamada aqui e um bug."""

    class _Mensagens:
        def create(self, **kwargs):
            raise AssertionError("/status e /start nao deveriam chamar a API da Anthropic")

    def __init__(self):
        self.messages = self._Mensagens()


class ClienteRedisFake:
    def __init__(self):
        self._dados: dict[str, str] = {}

    def get(self, chave: str) -> str | None:
        return self._dados.get(chave)

    def set(self, chave: str, valor: str) -> None:
        self._dados[chave] = valor

    def delete(self, chave: str) -> None:
        self._dados.pop(chave, None)

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


def test_start_reseta_historico_e_site_sem_chamar_anthropic():
    canal = CanalFake()
    repositorio = RepositorioEstadoMemoria()
    cliente_redis = ClienteRedisFake()

    repositorio.salvar("chat1", EstadoConversa(historico=[{"role": "user", "content": "oi"}]))
    salvar_site(cliente_redis, "chat1", "3gfoods")

    processar_mensagem(
        "chat1", "/start", cliente_redis, repositorio, ClienteAnthropicNuncaChamado(),
        tool_por_nome={}, canal=canal, modelo="modelo-qualquer",
    )

    assert repositorio.carregar("chat1").historico == []
    assert cliente_redis.get("site:chat1") is None
    assert len(canal.enviados) == 1
    assert "reiniciada" in canal.enviados[0][1].lower()


def test_start_e_case_insensitive_e_ignora_espacos():
    canal = CanalFake()
    processar_mensagem(
        "chat1", "  /Start  ", ClienteRedisFake(), RepositorioEstadoMemoria(), ClienteAnthropicNuncaChamado(),
        tool_por_nome={}, canal=canal, modelo="modelo-qualquer",
    )
    assert len(canal.enviados) == 1


def test_selecionar_site_disponivel_so_quando_site_ainda_nao_definido():
    cliente_redis = ClienteRedisFake()
    tools_sem_site, _ = _tools_e_executor(None, {}, cliente_redis, "chat1")
    tools_com_site, _ = _tools_e_executor("3gfoods", {}, cliente_redis, "chat1")

    assert "selecionar_site" in {t["name"] for t in tools_sem_site}
    assert "selecionar_site" not in {t["name"] for t in tools_com_site}
