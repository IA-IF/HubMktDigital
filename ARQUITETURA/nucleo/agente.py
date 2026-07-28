"""Loop de decisão do agente conversacional -- canal-agnóstico (ver
ARQUITETURA/entendimento.md: Telegram/IDE/outro são só transporte, sem
peso arquitetural). Não faz I/O próprio: cliente Anthropic (real ou
fake), execução de tool e canal de saída são todos injetados por quem
chama -- este módulo só cuida da mecânica do loop de tool-calls e da
distinção entre falha permanente e transitória.
"""
from dataclasses import dataclass, field
from typing import Callable, Protocol

from ARQUITETURA.nucleo.validacao_tool import InputInvalido, preparar_input


class FalhaPermanente(Exception):
    """Erro de execução de tool que NÃO adianta tentar de novo com o
    mesmo input (ex: proposta de campanha inválida) -- mensagem sempre
    segura de mostrar ao usuário."""


class FalhaTransitoria(Exception):
    """Erro de execução que PODE ser transitório (dependência
    faltando, rede, bug já corrigido) -- mensagem pode conter detalhe
    técnico, NUNCA mostrar direto ao usuário."""


@dataclass
class EstadoConversa:
    historico: list[dict] = field(default_factory=list)
    pendente: dict | None = None
    plano_aprovado: bool = False


class Canal(Protocol):
    def enviar(self, destinatario: str, texto: str) -> None: ...


class CanalFake:
    def __init__(self) -> None:
        self.enviados: list[tuple[str, str]] = []

    def enviar(self, destinatario: str, texto: str) -> None:
        self.enviados.append((destinatario, texto))


ExecutorTool = Callable[[str, dict], dict]


def _tool_por_nome(tools: list[dict], nome: str) -> dict | None:
    return next((t for t in tools if t["name"] == nome), None)


def _atualizar_tool_result(historico: list[dict], tool_use_id: str, novo_resultado) -> None:
    """Substitui, in-place, o conteudo do tool_result com esse
    tool_use_id -- nunca anexa um tool_result novo pro MESMO id (a API
    da Anthropic rejeita 2 tool_result pro mesmo tool_use)."""
    for turno in reversed(historico):
        if turno.get("role") != "user" or not isinstance(turno.get("content"), list):
            continue
        for bloco in turno["content"]:
            if isinstance(bloco, dict) and bloco.get("type") == "tool_result" and bloco.get("tool_use_id") == tool_use_id:
                bloco["content"] = str(novo_resultado)
                return


def _tool_ou_pendencia(bloco, tools: list[dict], executar_tool: ExecutorTool, estado: EstadoConversa):
    """Devolve (resultado, pendencia). `pendencia` preenchida so quando
    a tool precisa de confirmacao E o plano ainda nao foi aprovado --
    com plano_aprovado=True, executa direto (mesmo caminho de qualquer
    outra tool), permitindo encadear varios passos confirmados de uma
    vez so."""
    tool_meta = _tool_por_nome(tools, bloco.name)
    if tool_meta is None:
        return {"erro": f"ferramenta desconhecida: {bloco.name}"}, None
    if tool_meta.get("requer_confirmacao") and not estado.plano_aprovado:
        try:
            entrada_valida = preparar_input(bloco.input, tool_meta["input_schema"])
            pendencia = {"tool_use_id": bloco.id, "name": bloco.name, "input": entrada_valida}
            return {"ok": True, "aviso": "aguardando confirmacao do humano"}, pendencia
        except InputInvalido as exc:
            return {"erro": "input invalido, corrija e chame de novo", "problemas": exc.problemas}, None
    try:
        return executar_tool(bloco.name, bloco.input), None
    except FalhaPermanente as exc:
        return {"erro": str(exc)}, None
    except FalhaTransitoria:
        return {"erro": "falha tecnica temporaria"}, None


def _rodar_loop(
    cliente,
    modelo: str,
    system: str,
    tools: list[dict],
    estado: EstadoConversa,
    executar_tool: ExecutorTool,
    destinatario: str,
    canal: Canal,
    max_turnos: int,
) -> None:
    tools_api = [
        {"name": t["name"], "description": t["description"], "input_schema": t["input_schema"]}
        for t in tools
    ]

    for _ in range(max_turnos):
        resposta = cliente.messages.create(
            model=modelo, max_tokens=2000, system=system,
            tools=tools_api, messages=estado.historico,
        )
        blocos_tool = [b for b in resposta.content if b.type == "tool_use"]
        bloco_texto = next((b.text for b in resposta.content if b.type == "text"), None)
        estado.historico.append({"role": "assistant", "content": [b.model_dump() for b in resposta.content]})

        if not blocos_tool:
            if bloco_texto:
                canal.enviar(destinatario, bloco_texto)
            estado.plano_aprovado = False
            return

        resultados_tool = []
        pendencia_criada = None
        for bloco in blocos_tool:
            resultado, pendencia = _tool_ou_pendencia(bloco, tools, executar_tool, estado)
            if pendencia is not None:
                pendencia_criada = pendencia
            resultados_tool.append({
                "type": "tool_result", "tool_use_id": bloco.id,
                "content": str(resultado),
            })

        estado.historico.append({"role": "user", "content": resultados_tool})

        if pendencia_criada is not None:
            estado.pendente = pendencia_criada
            canal.enviar(destinatario, f"Proposta pronta ({pendencia_criada['name']}) -- confirma? (sim/nao)")
            return

    canal.enviar(destinatario, "Nao consegui concluir agora -- tenta reformular?")
    estado.plano_aprovado = False


def processar_turno(
    cliente,
    modelo: str,
    system: str,
    tools: list[dict],
    estado: EstadoConversa,
    texto_usuario: str,
    executar_tool: ExecutorTool,
    destinatario: str,
    canal: Canal,
    max_turnos: int = 6,
) -> None:
    estado.historico.append({"role": "user", "content": texto_usuario})
    _rodar_loop(cliente, modelo, system, tools, estado, executar_tool, destinatario, canal, max_turnos)


def resolver_pendencia(
    cliente,
    modelo: str,
    system: str,
    tools: list[dict],
    estado: EstadoConversa,
    confirmou: bool,
    executar_tool: ExecutorTool,
    destinatario: str,
    canal: Canal,
    max_turnos: int = 6,
) -> None:
    if estado.pendente is None:
        return
    pendente = estado.pendente

    if not confirmou:
        canal.enviar(destinatario, "Ok, cancelado.")
        estado.pendente = None
        estado.historico = []
        estado.plano_aprovado = False
        return

    estado.pendente = None
    try:
        resultado = executar_tool(pendente["name"], pendente["input"])
    except FalhaPermanente as exc:
        canal.enviar(destinatario, f"Nao consegui: {exc}. Ajusta o pedido e tenta de novo.")
        estado.historico = []
        estado.plano_aprovado = False
        return
    except FalhaTransitoria:
        estado.pendente = pendente
        canal.enviar(
            destinatario,
            "Erro tecnico, ja registrado pra investigar. Manda 'sim' de novo pra "
            "tentar mais uma vez, ou 'nao' pra cancelar.",
        )
        estado.plano_aprovado = False
        return

    # Plano aprovado: os proximos passos confirmados (ex: campanha
    # depois do orcamento) executam direto, sem pedir "sim" de novo --
    # reseta sozinho quando o loop termina ou falha permanentemente.
    estado.plano_aprovado = True
    # O tool_use que virou pendencia JA tem um tool_result placeholder
    # no historico (criado em _tool_ou_pendencia, "aguardando
    # confirmacao") -- atualiza esse bloco em vez de anexar um novo
    # tool_result pro MESMO tool_use_id (a API da Anthropic rejeita
    # dois tool_result pro mesmo id).
    _atualizar_tool_result(estado.historico, pendente["tool_use_id"], resultado)
    _rodar_loop(cliente, modelo, system, tools, estado, executar_tool, destinatario, canal, max_turnos)
