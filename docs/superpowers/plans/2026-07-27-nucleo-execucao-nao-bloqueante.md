# Núcleo v2 — execução não-bloqueante (despachante por chat) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resolver o problema real de hoje em produção -- o bot
(`AGENTES/julio/main_telegram.py`) é um loop único, single-thread: uma
mensagem que dispara uma tarefa demorada (`registrar_pedido_projeto` →
Planejador+Coder, minutos de chamadas sequenciais ao LLM) trava o
atendimento de QUALQUER outra conversa até terminar. Isso "parecia
travado" pro usuário mesmo estando só ocupado. Aqui: um despachante que
roda cada turno de conversa numa thread, paralelo ENTRE chats
diferentes, mas serializado DENTRO do mesmo chat (nunca dois turnos do
mesmo chat_id rodando ao mesmo tempo -- evitaria corromper
`EstadoConversa`).

**Architecture:** `DespachanteConcorrente` usa um
`ThreadPoolExecutor` (paralelismo real entre chats) + um lock por
`chat_id` (serialização dentro do mesmo chat). Quem chama só usa
`despachar(chat_id, tarefa)` -- não precisa saber de threading.

**Tech Stack:** Python 3.11+ (`concurrent.futures`, `threading`),
`pytest`.

## Global Constraints

- Não mexe em `AGENTES/julio/`, `TOOLS/`, `LEGADO/`.
- Testes determinísticos -- sem `time.sleep` como única forma de
  provar paralelismo (usa `threading.Barrier`, que só libera se as DUAS
  tarefas chegarem juntas -- prova real de execução concorrente, não
  só ausência de erro).

---

## File Structure

- Create: `ARQUITETURA/nucleo/execucao.py` — `DespachanteConcorrente`
- Create: `ARQUITETURA/nucleo/tests/test_execucao.py`

---

### Task 1: `DespachanteConcorrente` — paralelo entre chats, serial dentro do mesmo chat

**Files:**
- Create: `ARQUITETURA/nucleo/execucao.py`
- Test: `ARQUITETURA/nucleo/tests/test_execucao.py`

**Interfaces:**
- Produces:
  - `class DespachanteConcorrente(max_workers: int = 8)`.
  - `.despachar(chat_id: str, tarefa: Callable[[], None]) -> concurrent.futures.Future` —
    agenda `tarefa` pra rodar numa thread do pool; tarefas com o MESMO
    `chat_id` nunca rodam simultaneamente (lock por chat_id); tarefas
    de `chat_id` diferentes podem rodar ao mesmo tempo. Devolve o
    `Future` (quem chama pode `.result()` se precisar esperar, ou
    ignorar pra fire-and-forget).
  - `.encerrar(esperar: bool = True) -> None` — desliga o pool
    (`ThreadPoolExecutor.shutdown`).

- [x] **Step 1: Write the failing tests**

```python
# ARQUITETURA/nucleo/tests/test_execucao.py
import threading
import time

from ARQUITETURA.nucleo.execucao import DespachanteConcorrente


def test_despachante_roda_chats_diferentes_em_paralelo():
    """threading.Barrier(2) so libera as 2 tarefas se AMBAS chegarem
    nele -- se o despachante serializasse por engano (mesmo lock pra
    chats diferentes), uma das duas nunca chegaria e o teste travaria
    ate o timeout do Future.result() abaixo. Prova real de paralelismo,
    nao so ausencia de erro."""
    despachante = DespachanteConcorrente(max_workers=4)
    barreira = threading.Barrier(2, timeout=2)

    def tarefa():
        barreira.wait()

    futuro_1 = despachante.despachar("chat1", tarefa)
    futuro_2 = despachante.despachar("chat2", tarefa)
    futuro_1.result(timeout=3)
    futuro_2.result(timeout=3)
    despachante.encerrar()


def test_despachante_serializa_tarefas_do_mesmo_chat():
    despachante = DespachanteConcorrente(max_workers=4)
    ordem: list[str] = []
    lock_ordem = threading.Lock()
    liberar_a = threading.Event()

    def tarefa_a():
        with lock_ordem:
            ordem.append("a_inicio")
        assert liberar_a.wait(timeout=2), "tarefa_b nao deveria destravar tarefa_a"
        with lock_ordem:
            ordem.append("a_fim")

    def tarefa_b():
        with lock_ordem:
            ordem.append("b_inicio")

    futuro_a = despachante.despachar("chat1", tarefa_a)
    time.sleep(0.05)  # garante que tarefa_a ja comecou e esta esperando o evento
    futuro_b = despachante.despachar("chat1", tarefa_b)
    time.sleep(0.05)
    # tarefa_b nao pode ter comecado -- esta esperando o lock do chat1,
    # que so libera quando tarefa_a termina.
    assert ordem == ["a_inicio"]

    liberar_a.set()
    futuro_a.result(timeout=2)
    futuro_b.result(timeout=2)
    assert ordem == ["a_inicio", "a_fim", "b_inicio"]
    despachante.encerrar()


def test_despachante_propaga_excecao_via_future():
    despachante = DespachanteConcorrente(max_workers=2)

    def tarefa_com_erro():
        raise ValueError("erro de teste")

    futuro = despachante.despachar("chat1", tarefa_com_erro)
    try:
        futuro.result(timeout=2)
        assert False, "deveria ter levantado ValueError"
    except ValueError as exc:
        assert str(exc) == "erro de teste"
    despachante.encerrar()
```

- [x] **Step 2: Run tests to verify they fail**

Run: `pytest ARQUITETURA/nucleo/tests/test_execucao.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ARQUITETURA.nucleo.execucao'`

- [x] **Step 3: Write minimal implementation**

```python
# ARQUITETURA/nucleo/execucao.py
"""Despachante de turnos de conversa -- resolve o bug real de hoje: o
bot (AGENTES/julio/main_telegram.py) e um loop unico, single-thread,
onde uma tarefa demorada (ex: registrar_pedido_projeto rodando
Planejador+Coder por minutos) trava o atendimento de QUALQUER outra
conversa. Aqui, tarefas de chats DIFERENTES rodam em paralelo (thread
pool); tarefas do MESMO chat_id sao sempre serializadas (lock por
chat), pra nunca ter dois turnos da mesma conversa mutando
EstadoConversa ao mesmo tempo.
"""
import threading
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor


class DespachanteConcorrente:
    def __init__(self, max_workers: int = 8) -> None:
        self._pool = ThreadPoolExecutor(max_workers=max_workers)
        self._locks: dict[str, threading.Lock] = {}
        self._locks_guarda = threading.Lock()

    def _lock_do_chat(self, chat_id: str) -> threading.Lock:
        with self._locks_guarda:
            if chat_id not in self._locks:
                self._locks[chat_id] = threading.Lock()
            return self._locks[chat_id]

    def despachar(self, chat_id: str, tarefa: Callable[[], None]) -> Future:
        lock = self._lock_do_chat(chat_id)

        def rodar() -> None:
            with lock:
                tarefa()

        return self._pool.submit(rodar)

    def encerrar(self, esperar: bool = True) -> None:
        self._pool.shutdown(wait=esperar)
```

- [x] **Step 4: Run tests to verify they pass**

Run: `pytest ARQUITETURA/nucleo/tests/test_execucao.py -v`
Expected: PASS (3 tests)

- [x] **Step 5: Commit**

```bash
git add ARQUITETURA/nucleo/execucao.py ARQUITETURA/nucleo/tests/test_execucao.py
git commit -m "feat: DespachanteConcorrente - execucao nao-bloqueante por chat (nucleo v2)"
```

---

## Depois deste plano

Falta ainda: ligar `discover_tool`/`TOOLS/*` reais como `executar_tool`
de verdade (hoje é só um callback abstrato nos testes), montar um
`main.py` do núcleo que rode `Canal` real (Telegram e/ou IDE) usando
`DespachanteConcorrente` + `RepositorioEstadoRedis` juntos, e a
otimização de cada tool contra a documentação oficial de cada API
(ponto 1 do entendimento) — cada um é um plano separado. Só depois
desses é que faz sentido promover o núcleo a substituir
`AGENTES/julio/` em produção.
