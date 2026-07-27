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
