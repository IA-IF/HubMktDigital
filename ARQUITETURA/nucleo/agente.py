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
            return

        resultados_tool = []
        pendencia_criada = None
        for bloco in blocos_tool:
            tool_meta = _tool_por_nome(tools, bloco.name)
            if tool_meta is None:
                resultado = {"erro": f"ferramenta desconhecida: {bloco.name}"}
            elif tool_meta.get("requer_confirmacao"):
                try:
                    entrada_valida = preparar_input(bloco.input, tool_meta["input_schema"])
                    pendencia_criada = {
                        "tool_use_id": bloco.id, "name": bloco.name, "input": entrada_valida,
                    }
                    resultado = {"ok": True, "aviso": "aguardando confirmacao do humano"}
                except InputInvalido as exc:
                    resultado = {"erro": "input invalido, corrija e chame de novo", "problemas": exc.problemas}
            else:
                try:
                    resultado = executar_tool(bloco.name, bloco.input)
                except FalhaPermanente as exc:
                    resultado = {"erro": str(exc)}
                except FalhaTransitoria:
                    resultado = {"erro": "falha tecnica temporaria"}
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
