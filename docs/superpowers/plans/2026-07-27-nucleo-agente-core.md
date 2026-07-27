# Núcleo v2 — loop do agente (canal-agnóstico, retry preservando contexto) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir, em `ARQUITETURA/nucleo/agente.py`, o loop de
decisão do agente conversacional — canal-agnóstico (Telegram/IDE/outro
são só implementações de um `Canal` mínimo), usando o contrato de
validação de `validacao_tool.py` (Plano 1) antes de aceitar qualquer
input de tool que precise de confirmação humana, e distinguindo falha
permanente (não adianta insistir, cancela) de falha transitória
(preserva o estado pendente pra um retry direto) — generalizando o fix
aplicado hoje em produção (`PropostaInvalida` vs `RuntimeError` em
`AGENTES/julio/agentes.py`/`orchestrator.py`).

**Architecture:** Um módulo puro que recebe um `cliente` (qualquer
objeto com `.messages.create(...)` — o `anthropic.Anthropic()` real ou
o `ClienteAnthropicFake` do Plano 1) e um `executar_tool` (callback
injetado — quem chama decide COMO uma tool roda de verdade; este
módulo só cuida da mecânica do loop). Sem I/O próprio: quem chama
injeta cliente, execução de tool e canal de saída.

**Tech Stack:** Python 3.11+, `pytest`. Depende de
`ARQUITETURA/nucleo/validacao_tool.py` e
`ARQUITETURA/nucleo/fake_anthropic.py` (Plano 1, já implementados).

## Global Constraints

- Não mexe em `AGENTES/julio/`, `TOOLS/`, `LEGADO/` — código novo e
  independente.
- Não faz chamada de rede nem depende de Redis/Telegram/Anthropic de
  verdade — tudo injetado, testável 100% com fakes.
- Testes rodam com `pytest`, sem rede, sem credenciais.

---

## File Structure

- Create: `ARQUITETURA/nucleo/agente.py` — tipos base + `processar_turno`
  + `resolver_pendencia`
- Create: `ARQUITETURA/nucleo/tests/test_agente.py`

---

### Task 1: Tipos base — `EstadoConversa`, `Canal`, exceções de falha

**Files:**
- Create: `ARQUITETURA/nucleo/agente.py` (início do arquivo)
- Test: `ARQUITETURA/nucleo/tests/test_agente.py` (início do arquivo)

**Interfaces:**
- Produces:
  - `class FalhaPermanente(Exception)` — erro de execução de tool que
    NÃO adianta tentar de novo com o mesmo input (ex: proposta
    inválida). Mensagem de `str(exc)` sempre segura de mostrar ao
    usuário.
  - `class FalhaTransitoria(Exception)` — erro de execução que PODE
    ser transitório (dependência faltando, rede, bug já corrigido).
    Mensagem de `str(exc)` pode conter detalhe técnico — NUNCA mostrar
    direto ao usuário.
  - `class EstadoConversa` (dataclass, mutável): `historico: list[dict]`
    (default `[]`), `pendente: dict | None` (default `None`) — formato
    `{"tool_use_id": str, "name": str, "input": dict}`.
  - `class Canal(Protocol)`: `def enviar(self, destinatario: str, texto: str) -> None`.
  - `class CanalFake` — implementação de teste: guarda `.enviados: list[tuple[str, str]]`.

- [ ] **Step 1: Write the failing test**

```python
# ARQUITETURA/nucleo/tests/test_agente.py
from ARQUITETURA.nucleo.agente import (
    CanalFake,
    EstadoConversa,
    FalhaPermanente,
    FalhaTransitoria,
)


def test_canal_fake_registra_mensagens_enviadas():
    canal = CanalFake()
    canal.enviar("chat1", "ola")
    canal.enviar("chat1", "de novo")
    assert canal.enviados == [("chat1", "ola"), ("chat1", "de novo")]


def test_estado_conversa_default_vazio():
    estado = EstadoConversa()
    assert estado.historico == []
    assert estado.pendente is None


def test_falha_permanente_e_transitoria_sao_excecoes_distintas():
    assert issubclass(FalhaPermanente, Exception)
    assert issubclass(FalhaTransitoria, Exception)
    assert not issubclass(FalhaPermanente, FalhaTransitoria)
    assert not issubclass(FalhaTransitoria, FalhaPermanente)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest ARQUITETURA/nucleo/tests/test_agente.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ARQUITETURA.nucleo.agente'`

- [ ] **Step 3: Write minimal implementation**

```python
# ARQUITETURA/nucleo/agente.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest ARQUITETURA/nucleo/tests/test_agente.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add ARQUITETURA/nucleo/agente.py ARQUITETURA/nucleo/tests/test_agente.py
git commit -m "feat: tipos base do loop do agente (EstadoConversa/Canal/falhas) - nucleo v2"
```

---

### Task 2: `processar_turno` — loop de tool-calls com validação e pareamento

**Files:**
- Modify: `ARQUITETURA/nucleo/agente.py`
- Test: `ARQUITETURA/nucleo/tests/test_agente.py`

**Interfaces:**
- Consumes (de Task 1): `EstadoConversa`, `Canal`; de
  `validacao_tool.py` (Plano 1): `preparar_input(entrada, schema) -> dict`,
  `InputInvalido`.
- Produces:
  - `ExecutorTool = Callable[[str, dict], dict]` (alias de tipo) —
    `(nome_tool, input) -> resultado`; deve levantar `FalhaPermanente`
    ou `FalhaTransitoria` em caso de erro (nunca deixar outra exceção
    escapar).
  - `processar_turno(cliente, modelo: str, system: str, tools: list[dict],
    estado: EstadoConversa, texto_usuario: str, executar_tool: ExecutorTool,
    destinatario: str, canal: Canal, max_turnos: int = 6) -> None` —
    roda o loop; cada `tool` em `tools` é um dict com `name`,
    `description`, `input_schema`, e opcionalmente
    `requer_confirmacao: bool`. Efeitos: manda mensagens via
    `canal.enviar`; muta `estado.historico`/`estado.pendente` in-place.

- [ ] **Step 1: Write the failing tests**

```python
# adicionar ao final de ARQUITETURA/nucleo/tests/test_agente.py
from ARQUITETURA.nucleo.agente import processar_turno
from ARQUITETURA.nucleo.fake_anthropic import (
    ClienteAnthropicFake,
    fake_response,
    fake_text,
    fake_tool_use,
)

TOOL_SIMPLES = {
    "name": "somar",
    "description": "soma dois numeros",
    "input_schema": {
        "type": "object",
        "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
        "required": ["a", "b"],
    },
}

TOOL_CONFIRMACAO = {
    "name": "criar_campanha",
    "description": "cria campanha",
    "requer_confirmacao": True,
    "input_schema": {
        "type": "object",
        "properties": {
            "nome": {"type": "string"},
            "palavras_chave": {"type": "array"},
        },
        "required": ["nome", "palavras_chave"],
    },
}


def test_resposta_sem_tool_envia_texto_direto():
    cliente = ClienteAnthropicFake(respostas=[fake_response(fake_text("oi humano"))])
    canal = CanalFake()
    estado = EstadoConversa()
    processar_turno(
        cliente, "modelo-x", "sistema", [TOOL_SIMPLES], estado, "oi",
        executar_tool=lambda nome, entrada: {}, destinatario="chat1", canal=canal,
    )
    assert canal.enviados == [("chat1", "oi humano")]
    assert estado.pendente is None


def test_tool_sem_confirmacao_executa_e_continua():
    cliente = ClienteAnthropicFake(respostas=[
        fake_response(fake_tool_use(id="toolu_1", name="somar", input={"a": 2, "b": 3})),
        fake_response(fake_text("a soma deu 5")),
    ])
    canal = CanalFake()
    estado = EstadoConversa()
    chamadas = []

    def executar(nome, entrada):
        chamadas.append((nome, entrada))
        return {"resultado": entrada["a"] + entrada["b"]}

    processar_turno(
        cliente, "modelo-x", "sistema", [TOOL_SIMPLES], estado, "quanto e 2+3",
        executar_tool=executar, destinatario="chat1", canal=canal,
    )
    assert chamadas == [("somar", {"a": 2, "b": 3})]
    assert canal.enviados == [("chat1", "a soma deu 5")]
    assert estado.pendente is None


def test_tool_com_confirmacao_input_valido_cria_pendencia():
    cliente = ClienteAnthropicFake(respostas=[
        fake_response(fake_tool_use(
            id="toolu_1", name="criar_campanha",
            input={"nome": "X", "palavras_chave": ["a"]},
        )),
    ])
    canal = CanalFake()
    estado = EstadoConversa()
    processar_turno(
        cliente, "modelo-x", "sistema", [TOOL_CONFIRMACAO], estado, "cria a campanha",
        executar_tool=lambda nome, entrada: {}, destinatario="chat1", canal=canal,
    )
    assert estado.pendente == {
        "tool_use_id": "toolu_1", "name": "criar_campanha",
        "input": {"nome": "X", "palavras_chave": ["a"]},
    }
    assert len(canal.enviados) == 1
    assert "confirma" in canal.enviados[0][1].lower()


def test_tool_com_confirmacao_input_invalido_da_chance_de_corrigir():
    cliente = ClienteAnthropicFake(respostas=[
        fake_response(fake_tool_use(id="toolu_1", name="criar_campanha", input={"nome": "X"})),
        fake_response(fake_tool_use(
            id="toolu_2", name="criar_campanha",
            input={"nome": "X", "palavras_chave": ["a"]},
        )),
    ])
    canal = CanalFake()
    estado = EstadoConversa()
    processar_turno(
        cliente, "modelo-x", "sistema", [TOOL_CONFIRMACAO], estado, "cria a campanha",
        executar_tool=lambda nome, entrada: {}, destinatario="chat1", canal=canal,
    )
    # 1a tentativa invalida (faltou palavras_chave) nao virou pendencia;
    # o loop deu ao "modelo" (fake) a chance de corrigir na 2a chamada.
    assert estado.pendente == {
        "tool_use_id": "toolu_2", "name": "criar_campanha",
        "input": {"nome": "X", "palavras_chave": ["a"]},
    }


def test_tool_use_paralelo_todos_executam_e_pareiam():
    cliente = ClienteAnthropicFake(respostas=[
        fake_response(
            fake_tool_use(id="toolu_1", name="somar", input={"a": 1, "b": 1}),
            fake_tool_use(id="toolu_2", name="somar", input={"a": 2, "b": 2}),
        ),
        fake_response(fake_text("prontinho")),
    ])
    canal = CanalFake()
    estado = EstadoConversa()
    chamadas = []

    def executar(nome, entrada):
        chamadas.append(entrada)
        return {"resultado": entrada["a"] + entrada["b"]}

    processar_turno(
        cliente, "modelo-x", "sistema", [TOOL_SIMPLES], estado, "soma duas vezes",
        executar_tool=executar, destinatario="chat1", canal=canal,
    )
    assert chamadas == [{"a": 1, "b": 1}, {"a": 2, "b": 2}]
    assert canal.enviados == [("chat1", "prontinho")]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest ARQUITETURA/nucleo/tests/test_agente.py -v`
Expected: FAIL with `ImportError: cannot import name 'processar_turno'`

- [ ] **Step 3: Write minimal implementation**

```python
# adicionar ao final de ARQUITETURA/nucleo/agente.py
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
                except FalhaTransitoria as exc:
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest ARQUITETURA/nucleo/tests/test_agente.py -v`
Expected: PASS (8 tests total: 3 da Task 1 + 5 desta task)

- [ ] **Step 5: Commit**

```bash
git add ARQUITETURA/nucleo/agente.py ARQUITETURA/nucleo/tests/test_agente.py
git commit -m "feat: processar_turno - loop de tool-calls com validacao e pareamento (nucleo v2)"
```

---

### Task 3: `resolver_pendencia` — confirmar/cancelar preservando contexto na falha transitória

**Files:**
- Modify: `ARQUITETURA/nucleo/agente.py`
- Test: `ARQUITETURA/nucleo/tests/test_agente.py`

**Interfaces:**
- Consumes: `EstadoConversa`, `Canal`, `ExecutorTool`, `FalhaPermanente`,
  `FalhaTransitoria` (de Tasks 1-2).
- Produces:
  - `resolver_pendencia(estado: EstadoConversa, confirmou: bool,
    executar_tool: ExecutorTool, destinatario: str, canal: Canal) -> None`
    — se `estado.pendente is None`, não faz nada. Se `confirmou` é
    `False`: cancela (mensagem de cancelamento, zera `pendente` e
    `historico`). Se `True`: chama `executar_tool(pendente["name"],
    pendente["input"])`; sucesso → mensagem de sucesso, zera
    `pendente`/`historico`; `FalhaPermanente` → mostra o motivo direto
    (mensagem segura), zera `pendente`/`historico` (retry as-is não
    ajuda); `FalhaTransitoria` → mensagem genérica seguindo pedido de
    retry, **mantém `pendente`/`historico` intactos** (retry direto
    com "sim" de novo repete a MESMA ação).

- [ ] **Step 1: Write the failing tests**

```python
# adicionar ao final de ARQUITETURA/nucleo/tests/test_agente.py
from ARQUITETURA.nucleo.agente import resolver_pendencia

PENDENTE_EXEMPLO = {"tool_use_id": "toolu_1", "name": "criar_campanha", "input": {"nome": "X"}}


def test_resolver_pendencia_nao_confirma_cancela():
    canal = CanalFake()
    estado = EstadoConversa(historico=[{"role": "user", "content": "oi"}], pendente=PENDENTE_EXEMPLO)
    resolver_pendencia(estado, confirmou=False, executar_tool=lambda n, e: {}, destinatario="chat1", canal=canal)
    assert estado.pendente is None
    assert estado.historico == []
    assert "cancel" in canal.enviados[0][1].lower()


def test_resolver_pendencia_confirma_sucesso():
    canal = CanalFake()
    estado = EstadoConversa(pendente=PENDENTE_EXEMPLO)
    resolver_pendencia(
        estado, confirmou=True,
        executar_tool=lambda n, e: {"ok": True}, destinatario="chat1", canal=canal,
    )
    assert estado.pendente is None
    assert estado.historico == []
    assert len(canal.enviados) == 1


def test_resolver_pendencia_falha_permanente_cancela_e_explica():
    canal = CanalFake()
    estado = EstadoConversa(pendente=PENDENTE_EXEMPLO)

    def executar(nome, entrada):
        raise FalhaPermanente("titulo excede 30 caracteres")

    resolver_pendencia(estado, confirmou=True, executar_tool=executar, destinatario="chat1", canal=canal)
    assert estado.pendente is None
    assert "titulo excede 30 caracteres" in canal.enviados[0][1]


def test_resolver_pendencia_falha_transitoria_preserva_pendencia():
    canal = CanalFake()
    estado = EstadoConversa(pendente=dict(PENDENTE_EXEMPLO))

    def executar(nome, entrada):
        raise FalhaTransitoria("ModuleNotFoundError: no module google")

    resolver_pendencia(estado, confirmou=True, executar_tool=executar, destinatario="chat1", canal=canal)
    assert estado.pendente == PENDENTE_EXEMPLO
    assert "ModuleNotFoundError" not in canal.enviados[0][1]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest ARQUITETURA/nucleo/tests/test_agente.py -v`
Expected: FAIL with `ImportError: cannot import name 'resolver_pendencia'`

- [ ] **Step 3: Write minimal implementation**

```python
# adicionar ao final de ARQUITETURA/nucleo/agente.py
def resolver_pendencia(
    estado: EstadoConversa,
    confirmou: bool,
    executar_tool: ExecutorTool,
    destinatario: str,
    canal: Canal,
) -> None:
    if estado.pendente is None:
        return
    pendente = estado.pendente

    if not confirmou:
        canal.enviar(destinatario, "Ok, cancelado.")
        estado.pendente = None
        estado.historico = []
        return

    try:
        executar_tool(pendente["name"], pendente["input"])
        canal.enviar(destinatario, f"Feito: {pendente['name']} executado com sucesso.")
        estado.pendente = None
        estado.historico = []
    except FalhaPermanente as exc:
        canal.enviar(destinatario, f"Nao consegui: {exc}. Ajusta o pedido e tenta de novo.")
        estado.pendente = None
        estado.historico = []
    except FalhaTransitoria:
        canal.enviar(
            destinatario,
            "Erro tecnico, ja registrado pra investigar. Manda 'sim' de novo pra "
            "tentar mais uma vez, ou 'nao' pra cancelar.",
        )
        # Pendente/historico NAO zerados -- retry direto com "sim" repete a MESMA acao.
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest ARQUITETURA/nucleo/tests/test_agente.py -v`
Expected: PASS (12 tests total)

- [ ] **Step 5: Commit**

```bash
git add ARQUITETURA/nucleo/agente.py ARQUITETURA/nucleo/tests/test_agente.py
git commit -m "feat: resolver_pendencia - confirma/cancela preservando contexto na falha transitoria (nucleo v2)"
```

---

## Depois deste plano

Ainda faltam (próximos planos, cada um independente): memória Redis
real (ligar de volta o resumo já escrito), execução não-bloqueante
(rodar `executar_tool` sem travar o atendimento de outras conversas),
integração real com o catálogo de tools (`discover_tool`/`TOOLS/*`) e,
separadamente, a otimização de cada tool contra a documentação oficial
de cada API. Nenhum desses precisa acontecer antes de promover este
núcleo pra substituir `AGENTES/julio/` em produção — a promoção só
acontece quando o núcleo novo cobrir o que o antigo cobre hoje.
