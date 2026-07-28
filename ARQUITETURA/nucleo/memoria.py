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
        return EstadoConversa(
            historico=dados.get("historico", []),
            pendente=dados.get("pendente"),
            plano_aprovado=dados.get("plano_aprovado", False),
        )

    def salvar(self, chat_id: str, estado: EstadoConversa) -> None:
        dados = {
            "historico": estado.historico,
            "pendente": estado.pendente,
            "plano_aprovado": estado.plano_aprovado,
        }
        self._cliente.set(f"{self._prefixo}{chat_id}", json.dumps(dados, ensure_ascii=False))


def carregar_resumo(cliente_redis, chat_id: str, prefixo: str = "resumo:") -> str | None:
    return cliente_redis.get(f"{prefixo}{chat_id}")


def salvar_resumo(cliente_redis, chat_id: str, texto: str, prefixo: str = "resumo:") -> None:
    cliente_redis.set(f"{prefixo}{chat_id}", texto)


def carregar_site(cliente_redis, chat_id: str, prefixo: str = "site:") -> str | None:
    return cliente_redis.get(f"{prefixo}{chat_id}")


def salvar_site(cliente_redis, chat_id: str, site: str, prefixo: str = "site:") -> None:
    cliente_redis.set(f"{prefixo}{chat_id}", site)


def carregar_perfil_cliente(cliente_redis, site: str) -> dict:
    """Mesmo esquema de AGENTES/julio/perfil_cliente.py (hash
    cliente:<site>:perfil) -- compatibilidade se algum dia precisar
    ler o mesmo dado de lá."""
    return cliente_redis.hgetall(f"cliente:{site}:perfil")


def montar_system_com_perfil(
    system_base: str, site: str | None, perfil: dict, campos_esperados: list[str],
) -> str:
    """Ponto único de montagem do system prompt com o perfil de
    cliente -- mesmo princípio de `montar_system_com_resumo`: quem
    passar por aqui usa a memória de perfil automaticamente."""
    if site is None:
        return system_base
    linhas_perfil = [f"- {campo}: {perfil[campo]}" for campo in campos_esperados if campo in perfil]
    bloco_perfil = "\n".join(linhas_perfil) if linhas_perfil else "(perfil ainda vazio)"
    faltando = [c for c in campos_esperados if c not in perfil]
    texto_faltando = ", ".join(faltando) if faltando else "nenhum"
    return (
        f"{system_base}\n\n=== Perfil do cliente ({site}) ===\n{bloco_perfil}\n"
        f"Campos ainda faltando: {texto_faltando}. Só pergunte um campo faltando "
        "quando uma tarefa real precisar dele -- nunca faça entrevista completa "
        "de uma vez. Quando o humano responder, chame `atualizar_perfil_cliente`."
    )


def montar_system_com_resumo(system_base: str, resumo: str | None) -> str:
    """Ponto único de montagem do system prompt com o resumo de
    conversa -- qualquer chamador que passe por aqui usa a memória de
    volta automaticamente, sem depender de lembrar de ligar isso."""
    if not resumo:
        return system_base
    return f"{system_base}\n\n=== Resumo da conversa ate agora ===\n{resumo}"
