"""Persistência de EstadoConversa (Plano 2) -- hoje ela só vive em
memória de processo. RepositorioEstado é injetado (Protocol), com uma
implementação em memória (teste) e uma Redis real (produção, cliente
Redis também injetado -- este módulo nunca abre conexão própria).
"""
import json
from typing import Protocol

from ARQUITETURA.nucleo.agente import EstadoConversa


class RepositorioEstado(Protocol):
    def carregar(self, chat_id: str) -> EstadoConversa: ...
    def salvar(self, chat_id: str, estado: EstadoConversa) -> None: ...


class RepositorioEstadoMemoria:
    def __init__(self) -> None:
        self._dados: dict[str, EstadoConversa] = {}

    def carregar(self, chat_id: str) -> EstadoConversa:
        return self._dados.get(chat_id) or EstadoConversa()

    def salvar(self, chat_id: str, estado: EstadoConversa) -> None:
        self._dados[chat_id] = estado


class RepositorioEstadoRedis:
    def __init__(self, cliente_redis, prefixo: str = "estado:") -> None:
        self._cliente = cliente_redis
        self._prefixo = prefixo

    def carregar(self, chat_id: str) -> EstadoConversa:
        bruto = self._cliente.get(f"{self._prefixo}{chat_id}")
        if bruto is None:
            return EstadoConversa()
        dados = json.loads(bruto)
        return EstadoConversa(historico=dados.get("historico", []), pendente=dados.get("pendente"))

    def salvar(self, chat_id: str, estado: EstadoConversa) -> None:
        dados = {"historico": estado.historico, "pendente": estado.pendente}
        self._cliente.set(f"{self._prefixo}{chat_id}", json.dumps(dados, ensure_ascii=False))
