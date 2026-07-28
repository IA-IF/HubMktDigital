# Núcleo v2 — confirmação de uma vez pra sequência de passos ("plano aprovado") — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Corrigir o gap real achado no POC de execução genérica
(`docs/superpowers/plans/2026-07-27-poc-execucao-generica-ads.md`,
Task 3): confirmar uma ação que na prática exige VÁRIAS chamadas de
tool relacionadas (ex: orçamento → campanha → critério) hoje pede
confirmação humana a cada chamada individual, e `resolver_pendencia`
apaga o histórico depois da primeira, perdendo a referência (ex:
resource_name do orçamento) que os próximos passos precisam. Fix:
confirmação uma vez por INTENÇÃO do usuário; depois de confirmado, o
loop continua encadeando os passos técnicos necessários sem perguntar
de novo, até terminar ou falhar de verdade.

**Architecture:** `EstadoConversa` ganha `plano_aprovado: bool`. Tools
`requer_confirmacao` só criam pendência quando `plano_aprovado` é
`False`; quando é `True`, executam direto (mesma lógica de qualquer
outra tool). O loop de tool-calling (hoje duplicado entre
`processar_turno` e o final de `resolver_pendencia`) vira uma função
interna compartilhada (`_rodar_loop`), pra `resolver_pendencia`
continuar o MESMO mecanismo depois de confirmar, em vez de só executar
uma chamada isolada. `plano_aprovado` reseta pra `False`
automaticamente quando o agente termina (sem mais tool_use) ou quando
uma falha permanente cancela o fluxo — sempre volta a pedir confirmação
pra próxima ação nova do usuário. Como `EstadoConversa` já é persistido
via `RepositorioEstadoRedis` (Plano 3), `plano_aprovado` fica salvo no
Redis automaticamente, sem trabalho extra — satisfaz o requisito do
usuário ("o que precisa de decisão humana tem que ser perguntado e
salvo no Redis").

**Tech Stack:** Python 3.11+, `pytest`. Modifica
`ARQUITETURA/nucleo/agente.py` (Plano 2) e o call site em
`ARQUITETURA/nucleo/main.py`.

## Global Constraints

- Não quebra nenhum teste já existente de `test_agente.py` sem motivo
  — ajustar os que dependem da assinatura antiga de
  `resolver_pendencia` (agora precisa de `cliente`/`modelo`/`system`/
  `tools`/`max_turnos` pra poder continuar o loop).
- Não muda `memoria.py`/`RepositorioEstadoRedis` — `plano_aprovado`
  é só mais um campo do dataclass já serializado.

---

## File Structure

- Modify: `ARQUITETURA/nucleo/agente.py`
- Modify: `ARQUITETURA/nucleo/tests/test_agente.py`
- Modify: `ARQUITETURA/nucleo/memoria.py` (serializar/desserializar o
  novo campo `plano_aprovado`)
- Modify: `ARQUITETURA/nucleo/tests/test_memoria.py`
- Modify: `ARQUITETURA/nucleo/main.py` (novo call site de
  `resolver_pendencia`)

---

### Task 1: `plano_aprovado` em `EstadoConversa` + persistência

**Files:**
- Modify: `ARQUITETURA/nucleo/agente.py`
- Modify: `ARQUITETURA/nucleo/memoria.py`
- Modify: `ARQUITETURA/nucleo/tests/test_agente.py`
- Modify: `ARQUITETURA/nucleo/tests/test_memoria.py`

**Interfaces:**
- Produces: `EstadoConversa.plano_aprovado: bool` (default `False`).
  `RepositorioEstadoRedis.salvar`/`.carregar` incluem esse campo no
  JSON persistido.

- [ ] **Step 1: Write the failing tests**

```python
# adicionar em ARQUITETURA/nucleo/tests/test_agente.py
def test_estado_conversa_plano_aprovado_default_false():
    estado = EstadoConversa()
    assert estado.plano_aprovado is False
```

```python
# adicionar em ARQUITETURA/nucleo/tests/test_memoria.py
def test_repositorio_redis_persiste_plano_aprovado():
    cliente = ClienteRedisFake()
    repo = RepositorioEstadoRedis(cliente)
    estado = EstadoConversa(plano_aprovado=True)
    repo.salvar("chat1", estado)
    recarregado = repo.carregar("chat1")
    assert recarregado.plano_aprovado is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest ARQUITETURA/nucleo/tests/test_agente.py::test_estado_conversa_plano_aprovado_default_false ARQUITETURA/nucleo/tests/test_memoria.py::test_repositorio_redis_persiste_plano_aprovado -v`
Expected: FAIL (`AttributeError`/`assert False is True`)

- [ ] **Step 3: Write minimal implementation**

```python
# ARQUITETURA/nucleo/agente.py -- EstadoConversa
@dataclass
class EstadoConversa:
    historico: list[dict] = field(default_factory=list)
    pendente: dict | None = None
    plano_aprovado: bool = False
```

```python
# ARQUITETURA/nucleo/memoria.py -- RepositorioEstadoRedis
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest ARQUITETURA/ -v`
Expected: PASS (todos os testes existentes + os 2 novos)

- [ ] **Step 5: Commit**

```bash
git add ARQUITETURA/nucleo/agente.py ARQUITETURA/nucleo/memoria.py ARQUITETURA/nucleo/tests/test_agente.py ARQUITETURA/nucleo/tests/test_memoria.py
git commit -m "feat: EstadoConversa.plano_aprovado, persistido no Redis (nucleo v2)"
```

---

### Task 2: loop compartilhado + `resolver_pendencia` encadeia passos sem re-perguntar

**Files:**
- Modify: `ARQUITETURA/nucleo/agente.py`
- Modify: `ARQUITETURA/nucleo/tests/test_agente.py`
- Modify: `ARQUITETURA/nucleo/main.py`

**Interfaces:**
- Produces:
  - `resolver_pendencia(cliente, modelo: str, system: str, tools: list[dict], estado: EstadoConversa, confirmou: bool, executar_tool: ExecutorTool, destinatario: str, canal: Canal, max_turnos: int = 6) -> None`
    — **assinatura nova** (antes não tinha `cliente`/`modelo`/`system`/
    `tools`/`max_turnos`). Ao confirmar: executa a ação pendente,
    marca `estado.plano_aprovado = True`, alimenta o resultado de
    volta no histórico, e CONTINUA o mesmo loop de tool-calling (via
    `_rodar_loop` interno) -- deixando o agente decidir o próximo
    passo. Tools `requer_confirmacao` chamadas enquanto
    `plano_aprovado` é `True` executam direto, sem nova pendência.
    `plano_aprovado` volta a `False` quando o loop termina (sem mais
    tool_use) ou falha permanentemente.
- Consumes: mesma interface de `processar_turno` (agora ambos chamam o
  mesmo `_rodar_loop` interno).

- [ ] **Step 1: Write the failing tests**

```python
# adicionar em ARQUITETURA/nucleo/tests/test_agente.py
def test_plano_aprovado_permite_tool_requer_confirmacao_direto_sem_pendencia():
    """Confirma o 1o passo (orcamento); o agente decide criar a
    campanha em seguida (2o passo, MESMA tool requer_confirmacao) --
    com plano_aprovado=True, executa direto, sem pedir confirmacao de
    novo."""
    cliente = ClienteAnthropicFake(respostas=[
        # resposta 1: decide criar orcamento (tool requer_confirmacao)
        fake_response(fake_tool_use(id="toolu_1", name="criar_campanha", input={"nome": "orcamento"})),
    ])
    canal = CanalFake()
    estado = EstadoConversa()
    chamadas = []

    def executar(nome, entrada):
        chamadas.append(entrada)
        return {"ok": True, "resource_name": f"recurso/{len(chamadas)}"}

    processar_turno(
        cliente, "modelo-x", "sistema", [TOOL_CONFIRMACAO_SIMPLES], estado, "cria a campanha completa",
        executar_tool=executar, destinatario="chat1", canal=canal,
    )
    assert estado.pendente is not None
    assert estado.plano_aprovado is False

    # confirma -- o proximo "turno" do fake decide fazer MAIS UMA chamada
    # da MESMA tool requer_confirmacao (2o passo do plano), e so depois
    # para (texto final, sem tool_use)
    cliente_confirmacao = ClienteAnthropicFake(respostas=[
        fake_response(fake_tool_use(id="toolu_2", name="criar_campanha", input={"nome": "campanha real"})),
        fake_response(fake_text("prontinho, plano concluido")),
    ])
    resolver_pendencia(
        cliente_confirmacao, "modelo-x", "sistema", [TOOL_CONFIRMACAO_SIMPLES], estado,
        confirmou=True, executar_tool=executar, destinatario="chat1", canal=canal,
    )

    # os 2 passos executaram (orcamento na 1a chamada direta do resolver,
    # campanha na 2a -- SEM pendencia nova no meio)
    assert len(chamadas) == 2
    assert estado.pendente is None
    assert estado.plano_aprovado is False
    assert any("prontinho" in msg for _, msg in canal.enviados)


def test_resolver_pendencia_falha_transitoria_preserva_plano_e_pendencia():
    canal = CanalFake()
    estado = EstadoConversa(pendente=dict(PENDENTE_EXEMPLO))

    def executar(nome, entrada):
        raise FalhaTransitoria("erro tecnico")

    resolver_pendencia(
        ClienteAnthropicFake(respostas=[]), "modelo-x", "sistema", [], estado,
        confirmou=True, executar_tool=executar, destinatario="chat1", canal=canal,
    )
    assert estado.pendente == PENDENTE_EXEMPLO
    assert estado.plano_aprovado is False
```

Nota: `TOOL_CONFIRMACAO_SIMPLES` é uma variante de `TOOL_CONFIRMACAO`
já existente no arquivo, mas sem campos obrigatórios (só `{"nome":
{"type": "string"}}`, `required: ["nome"]`) pra simplificar o teste de
encadeamento -- adicionar essa constante junto dos testes.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest ARQUITETURA/nucleo/tests/test_agente.py -v`
Expected: FAIL (`resolver_pendencia() missing required positional arguments` e afins)

- [ ] **Step 3: Write minimal implementation**

```python
# ARQUITETURA/nucleo/agente.py -- substituir processar_turno/resolver_pendencia
def _tool_ou_pendencia(bloco, tools, executar_tool, estado: EstadoConversa):
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
    cliente, modelo: str, system: str, tools: list[dict], estado: EstadoConversa,
    executar_tool: ExecutorTool, destinatario: str, canal: Canal, max_turnos: int,
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
                "type": "tool_result", "tool_use_id": bloco.id, "content": str(resultado),
            })

        estado.historico.append({"role": "user", "content": resultados_tool})

        if pendencia_criada is not None:
            estado.pendente = pendencia_criada
            canal.enviar(destinatario, f"Proposta pronta ({pendencia_criada['name']}) -- confirma? (sim/nao)")
            return

    canal.enviar(destinatario, "Nao consegui concluir agora -- tenta reformular?")
    estado.plano_aprovado = False


def processar_turno(
    cliente, modelo: str, system: str, tools: list[dict], estado: EstadoConversa,
    texto_usuario: str, executar_tool: ExecutorTool, destinatario: str, canal: Canal,
    max_turnos: int = 6,
) -> None:
    estado.historico.append({"role": "user", "content": texto_usuario})
    _rodar_loop(cliente, modelo, system, tools, estado, executar_tool, destinatario, canal, max_turnos)


def resolver_pendencia(
    cliente, modelo: str, system: str, tools: list[dict], estado: EstadoConversa,
    confirmou: bool, executar_tool: ExecutorTool, destinatario: str, canal: Canal,
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

    estado.plano_aprovado = True
    estado.historico.append({
        "role": "user",
        "content": [{"type": "tool_result", "tool_use_id": pendente["tool_use_id"], "content": str(resultado)}],
    })
    _rodar_loop(cliente, modelo, system, tools, estado, executar_tool, destinatario, canal, max_turnos)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest ARQUITETURA/ -v`
Expected: PASS (todos, incluindo os 2 novos)

- [ ] **Step 5: Update `main.py` call site**

```python
# ARQUITETURA/nucleo/main.py -- dentro de processar_mensagem
    if estado.pendente is not None and resposta_baixa in ("sim", "s", "nao", "n"):
        resolver_pendencia(
            cliente_anthropic, modelo, system, tools, estado,
            confirmou=resposta_baixa in ("sim", "s"),
            executar_tool=executar_tool, destinatario=chat_id, canal=canal,
        )
```

- [ ] **Step 6: Commit**

```bash
git add ARQUITETURA/nucleo/agente.py ARQUITETURA/nucleo/tests/test_agente.py ARQUITETURA/nucleo/main.py
git commit -m "feat: plano aprovado encadeia passos confirmados uma vez so (nucleo v2)"
```

---

## Depois deste plano

Rodar de novo o teste real do POC (Task 3 de
`2026-07-27-poc-execucao-generica-ads.md`) — dessa vez esperando UMA
confirmação só cobrindo orçamento + campanha + critério de
proximidade, não uma por passo.
