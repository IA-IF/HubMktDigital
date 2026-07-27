# Núcleo v2 — memória Redis real (persistência + resumo lido de volta) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dar a `EstadoConversa` (Plano 2) persistência real via Redis
— hoje ela só existe como objeto Python em memória, se perde a cada
reinício — e consertar o bug concreto encontrado em produção hoje: o
"resumo de conversa" era escrito a cada turno (`_atualizar_resumo` em
`AGENTES/julio/orchestrator.py`) e **nunca lido de volta** pra informar
a próxima decisão do modelo. Aqui o resumo é modelado desde o início
como algo que É lido de volta.

**Architecture:** `RepositorioEstado` é um `Protocol` (mesma ideia do
`Canal` no Plano 2) com duas implementações: `RepositorioEstadoMemoria`
(dict, pra teste) e `RepositorioEstadoRedis` (Redis de verdade,
injetado). O resumo vive como uma função pura,
`montar_system_com_resumo`, que qualquer chamador usa pra montar o
`system` do `processar_turno` incluindo o resumo carregado — assim é
estruturalmente impossível "esquecer" de usar o resumo, porque ele faz
parte da montagem do prompt, não um extra opcional.

**Tech Stack:** Python 3.11+, `pytest`. Depende de
`ARQUITETURA/nucleo/agente.py` (Plano 2, `EstadoConversa`).

## Global Constraints

- Não mexe em `AGENTES/julio/`, `TOOLS/`, `LEGADO/`.
- Testes não abrem conexão de rede com Redis de verdade — usam um
  cliente Redis fake mínimo (só `.get`/`.set`, os únicos métodos
  usados aqui) definido no próprio arquivo de teste.
- `RepositorioEstadoRedis` recebe o cliente Redis por injeção
  (construtor) — nunca cria sua própria conexão.

---

## File Structure

- Create: `ARQUITETURA/nucleo/memoria.py` — `RepositorioEstado`
  (Protocol), `RepositorioEstadoMemoria`, `RepositorioEstadoRedis`,
  `carregar_resumo`, `salvar_resumo`, `montar_system_com_resumo`
- Create: `ARQUITETURA/nucleo/tests/test_memoria.py`

---

### Task 1: `RepositorioEstado` — persistência de `EstadoConversa`

**Files:**
- Create: `ARQUITETURA/nucleo/memoria.py`
- Test: `ARQUITETURA/nucleo/tests/test_memoria.py`

**Interfaces:**
- Consumes: `EstadoConversa` (de `ARQUITETURA.nucleo.agente`, Plano 2).
- Produces:
  - `class RepositorioEstado(Protocol)`: `carregar(chat_id: str) -> EstadoConversa`,
    `salvar(chat_id: str, estado: EstadoConversa) -> None`.
  - `class RepositorioEstadoMemoria` — dict interno, implementa o
    protocolo acima; `carregar` de chat_id nunca visto devolve
    `EstadoConversa()` novo (nunca `None`).
  - `class RepositorioEstadoRedis(cliente_redis, prefixo: str = "estado:")` —
    implementa o protocolo usando `cliente_redis.get(chave)`/`.set(chave, valor)`
    com serialização JSON (`{"historico": [...], "pendente": {...}|None}`);
    `carregar` de chave ausente (`cliente_redis.get` devolve `None`)
    devolve `EstadoConversa()` novo.

- [x] **Step 1: Write the failing tests**

```python
# ARQUITETURA/nucleo/tests/test_memoria.py
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
    assert json.loads(bruto) == {"historico": [{"role": "user", "content": "oi"}], "pendente": {"x": 1}}

    recarregado = repo.carregar("chat1")
    assert recarregado.historico == estado.historico
    assert recarregado.pendente == estado.pendente


def test_repositorio_redis_usa_prefixo_customizado():
    cliente = ClienteRedisFake()
    repo = RepositorioEstadoRedis(cliente, prefixo="outro:")
    repo.salvar("chat1", EstadoConversa())
    assert "outro:chat1" in cliente._dados
```

- [x] **Step 2: Run tests to verify they fail**

Run: `pytest ARQUITETURA/nucleo/tests/test_memoria.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ARQUITETURA.nucleo.memoria'`

- [x] **Step 3: Write minimal implementation**

```python
# ARQUITETURA/nucleo/memoria.py
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
```

- [x] **Step 4: Run tests to verify they pass**

Run: `pytest ARQUITETURA/nucleo/tests/test_memoria.py -v`
Expected: PASS (5 tests)

- [x] **Step 5: Commit**

```bash
git add ARQUITETURA/nucleo/memoria.py ARQUITETURA/nucleo/tests/test_memoria.py
git commit -m "feat: RepositorioEstado - persistencia real de EstadoConversa (nucleo v2)"
```

---

### Task 2: Resumo de conversa — escrito E lido de volta

**Files:**
- Modify: `ARQUITETURA/nucleo/memoria.py`
- Test: `ARQUITETURA/nucleo/tests/test_memoria.py`

**Interfaces:**
- Consumes: nada novo (usa o mesmo `ClienteRedisFake`/cliente Redis
  real via `.get`/`.set`).
- Produces:
  - `carregar_resumo(cliente_redis, chat_id: str, prefixo: str = "resumo:") -> str | None`
    — `None` se nunca houve resumo salvo pra esse chat.
  - `salvar_resumo(cliente_redis, chat_id: str, texto: str, prefixo: str = "resumo:") -> None`.
  - `montar_system_com_resumo(system_base: str, resumo: str | None) -> str`
    — se `resumo` for `None` ou string vazia, devolve `system_base` sem
    alteração; senão devolve `system_base` com uma seção extra
    `"\n\n=== Resumo da conversa ate agora ===\n{resumo}"` anexada.
    **Esta função é o ponto que fecha o bug de hoje**: qualquer
    chamador que monte o `system` do `processar_turno` passando por
    aqui automaticamente usa o resumo — não dá pra "esquecer" de ligar
    a memória de volta, porque monta o prompt inteiro numa função só.

- [x] **Step 1: Write the failing tests**

```python
# adicionar ao final de ARQUITETURA/nucleo/tests/test_memoria.py
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
```

- [x] **Step 2: Run tests to verify they fail**

Run: `pytest ARQUITETURA/nucleo/tests/test_memoria.py -v`
Expected: FAIL with `ImportError: cannot import name 'carregar_resumo'`

- [x] **Step 3: Write minimal implementation**

```python
# adicionar ao final de ARQUITETURA/nucleo/memoria.py
def carregar_resumo(cliente_redis, chat_id: str, prefixo: str = "resumo:") -> str | None:
    return cliente_redis.get(f"{prefixo}{chat_id}")


def salvar_resumo(cliente_redis, chat_id: str, texto: str, prefixo: str = "resumo:") -> None:
    cliente_redis.set(f"{prefixo}{chat_id}", texto)


def montar_system_com_resumo(system_base: str, resumo: str | None) -> str:
    """Ponto único de montagem do system prompt com o resumo de
    conversa -- qualquer chamador que passe por aqui usa a memória de
    volta automaticamente, sem depender de lembrar de ligar isso."""
    if not resumo:
        return system_base
    return f"{system_base}\n\n=== Resumo da conversa ate agora ===\n{resumo}"
```

- [x] **Step 4: Run tests to verify they pass**

Run: `pytest ARQUITETURA/nucleo/tests/test_memoria.py -v`
Expected: PASS (9 tests total)

- [x] **Step 5: Commit**

```bash
git add ARQUITETURA/nucleo/memoria.py ARQUITETURA/nucleo/tests/test_memoria.py
git commit -m "feat: resumo de conversa lido de volta no system prompt (nucleo v2)"
```

---

## Depois deste plano

Falta ainda: execução não-bloqueante (rodar `executar_tool` sem travar
o atendimento de outras conversas), integração real com
Redis/discover_tool/TOOLS para virar o `executar_tool` de verdade (hoje
é só um callback abstrato nos testes), e a otimização de cada tool
contra a documentação oficial de cada API — cada um desses é um plano
separado.
