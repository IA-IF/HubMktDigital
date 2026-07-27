# Núcleo v2 — contrato de validação + harness de teste sem LLM real — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir, em `ARQUITETURA/nucleo/` (código novo, não toca em
`AGENTES/julio/` que continua em produção), as duas peças de infra mais
alavancadas da nova arquitetura: (1) um contrato único e reutilizável
de validação/reparo de input de tool (generaliza os fixes ad hoc feitos
hoje em `orchestrator.py` durante a sessão de bugs), e (2) um "cliente
Anthropic fake" — test double scriptável que imita a interface real de
`anthropic.Anthropic().messages.create()` — pra testar mecânica de
loop de tool-calls (pareamento tool_use/tool_result, tool_use paralelo,
retry) sem gastar token real. Essas duas peças são pré-requisito de
qualquer reescrita futura do agente conversacional.

**Architecture:** Duas bibliotecas Python puras, sem I/O de rede, sem
dependência de Redis/Anthropic/Telegram — só stdlib + o schema JSON de
uma tool como entrada. `validacao_tool.py` é usado pelo futuro
orquestrador antes de aceitar um `tool_use.input` como válido.
`fake_anthropic.py` é usado só em testes, nunca em produção.

**Tech Stack:** Python 3.11+, `pytest`.

## Global Constraints

- Nada aqui importa de `AGENTES/julio/`, `TOOLS/`, ou `LEGADO/` — é
  código novo e independente, mesmo que a lógica de `validacao_tool.py`
  seja inspirada no que já existe em `AGENTES/julio/orchestrator.py`
  (`_corrigir_tipos_input`/`_validar_input_schema`).
- Não mexe em nada que roda em produção (bot Telegram na EC2
  continua intocado).
- Testes rodam com `pytest`, sem rede, sem credenciais.

---

## File Structure

- Create: `ARQUITETURA/nucleo/__init__.py` (pacote vazio)
- Create: `ARQUITETURA/nucleo/validacao_tool.py` — contrato de
  validação/reparo de input de tool contra seu próprio `input_schema`
- Create: `ARQUITETURA/nucleo/tests/__init__.py` (pacote vazio)
- Create: `ARQUITETURA/nucleo/tests/test_validacao_tool.py`
- Create: `ARQUITETURA/nucleo/fake_anthropic.py` — test double da API
  da Anthropic, scriptável, pra testar loop de tool-calls sem gastar
  token
- Create: `ARQUITETURA/nucleo/tests/test_fake_anthropic.py`

---

### Task 1: `validacao_tool.py` — contrato de validação/reparo de input

**Files:**
- Create: `ARQUITETURA/nucleo/validacao_tool.py`
- Test: `ARQUITETURA/nucleo/tests/test_validacao_tool.py`

**Interfaces:**
- Produces:
  - `class InputInvalido(Exception)` — levantada por `preparar_input`
    quando sobra problema depois da correção de tipo; `.problemas` é
    `list[str]` com os motivos.
  - `corrigir_tipos_input(entrada: dict, schema: dict) -> dict` — pura,
    sem side-effect, devolve uma CÓPIA de `entrada` com qualquer campo
    declarado `"type": "array"`/`"object"` no schema, que tenha chegado
    como `str`, desserializado via `json.loads` (best-effort: se não
    for JSON válido, mantém como veio).
  - `validar_input_schema(entrada: dict, schema: dict) -> list[str]` —
    pura, devolve lista de problemas (vazia = ok): checa `required` do
    schema (ausente ou vazio) e checa o `type` declarado bate com o
    tipo Python de cada campo presente (`string`→`str`,
    `number`→`(int,float)`, `integer`→`int`, `array`→`list`,
    `object`→`dict`, `boolean`→`bool`).
  - `preparar_input(entrada: dict, schema: dict) -> dict` — chama
    `corrigir_tipos_input` seguido de `validar_input_schema`; se a
    lista de problemas não for vazia, levanta `InputInvalido(problemas)`;
    senão devolve o `entrada` corrigido.

- [x] **Step 1: Write the failing tests**

```python
# ARQUITETURA/nucleo/tests/test_validacao_tool.py
import pytest

from ARQUITETURA.nucleo.validacao_tool import (
    InputInvalido,
    corrigir_tipos_input,
    preparar_input,
    validar_input_schema,
)

SCHEMA = {
    "type": "object",
    "properties": {
        "nome": {"type": "string"},
        "orcamento": {"type": "number"},
        "palavras_chave": {"type": "array"},
    },
    "required": ["nome", "orcamento", "palavras_chave"],
}


def test_corrigir_tipos_desserializa_array_vindo_como_string():
    entrada = {"nome": "X", "orcamento": 10, "palavras_chave": '[{"texto": "a"}]'}
    corrigido = corrigir_tipos_input(entrada, SCHEMA)
    assert corrigido["palavras_chave"] == [{"texto": "a"}]


def test_corrigir_tipos_mantem_string_invalida_como_veio():
    entrada = {"nome": "X", "orcamento": 10, "palavras_chave": "nao e json"}
    corrigido = corrigir_tipos_input(entrada, SCHEMA)
    assert corrigido["palavras_chave"] == "nao e json"


def test_corrigir_tipos_nao_muta_entrada_original():
    entrada = {"nome": "X", "orcamento": 10, "palavras_chave": '["a"]'}
    corrigir_tipos_input(entrada, SCHEMA)
    assert entrada["palavras_chave"] == '["a"]'


def test_validar_schema_pega_campo_obrigatorio_ausente():
    entrada = {"nome": "X", "orcamento": 10}
    problemas = validar_input_schema(entrada, SCHEMA)
    assert any("palavras_chave" in p for p in problemas)


def test_validar_schema_pega_tipo_errado():
    entrada = {"nome": "X", "orcamento": "dez", "palavras_chave": ["a"]}
    problemas = validar_input_schema(entrada, SCHEMA)
    assert any("orcamento" in p for p in problemas)


def test_validar_schema_ok_sem_problemas():
    entrada = {"nome": "X", "orcamento": 10, "palavras_chave": ["a"]}
    assert validar_input_schema(entrada, SCHEMA) == []


def test_preparar_input_corrige_e_devolve_quando_valido():
    entrada = {"nome": "X", "orcamento": 10, "palavras_chave": '["a"]'}
    resultado = preparar_input(entrada, SCHEMA)
    assert resultado == {"nome": "X", "orcamento": 10, "palavras_chave": ["a"]}


def test_preparar_input_levanta_quando_invalido():
    entrada = {"orcamento": "dez"}
    with pytest.raises(InputInvalido) as exc_info:
        preparar_input(entrada, SCHEMA)
    problemas = exc_info.value.problemas
    assert any("nome" in p for p in problemas)
    assert any("orcamento" in p for p in problemas)
    assert any("palavras_chave" in p for p in problemas)
```

- [x] **Step 2: Run tests to verify they fail**

Run: `pytest ARQUITETURA/nucleo/tests/test_validacao_tool.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ARQUITETURA.nucleo.validacao_tool'`

- [x] **Step 3: Write minimal implementation**

```python
# ARQUITETURA/nucleo/validacao_tool.py
"""Contrato único de validação/reparo entre "o que o LLM decidiu
chamar" (tool_use.input) e "o que vai executar de verdade". A API da
Anthropic usa o input_schema de uma tool só como sugestão pro modelo —
não garante nem tipo nem campo obrigatório. Isso generaliza os fixes
ad hoc feitos em AGENTES/julio/orchestrator.py (_corrigir_tipos_input/
_validar_input_schema) numa peça reutilizável por qualquer chamador.
"""
import json

_TIPO_JSON_PARA_PYTHON = {
    "string": str,
    "number": (int, float),
    "integer": int,
    "array": list,
    "object": dict,
    "boolean": bool,
}


class InputInvalido(Exception):
    def __init__(self, problemas: list[str]):
        super().__init__("; ".join(problemas))
        self.problemas = problemas


def corrigir_tipos_input(entrada: dict, schema: dict) -> dict:
    """Alguns modelos serializam um campo array/object em DUAS camadas
    -- mandam a string JSON em vez da lista/objeto de verdade. Tenta
    desserializar antes de validar; se não for JSON válido, mantém
    como veio (a validação de tipo abaixo vai pegar isso)."""
    propriedades = schema.get("properties", {})
    corrigido = dict(entrada)
    for campo, valor in entrada.items():
        esperado = propriedades.get(campo, {}).get("type")
        if esperado in ("array", "object") and isinstance(valor, str):
            try:
                corrigido[campo] = json.loads(valor)
            except json.JSONDecodeError:
                pass
    return corrigido


def validar_input_schema(entrada: dict, schema: dict) -> list[str]:
    """Validação mínima e genérica: campo obrigatório presente e tipo
    Python bate com o `type` declarado no schema."""
    propriedades = schema.get("properties", {})
    problemas = []
    for campo in schema.get("required", []):
        if campo not in entrada or entrada[campo] in (None, "", []):
            problemas.append(f"{campo}: obrigatorio e ausente")
            continue
        tipo_esperado = _TIPO_JSON_PARA_PYTHON.get(propriedades.get(campo, {}).get("type"))
        if tipo_esperado and not isinstance(entrada[campo], tipo_esperado):
            problemas.append(
                f"{campo}: deveria ser {propriedades[campo]['type']}, "
                f"veio {type(entrada[campo]).__name__} ({entrada[campo]!r})"
            )
    return problemas


def preparar_input(entrada: dict, schema: dict) -> dict:
    """Corrige tipos e valida contra o schema. Levanta InputInvalido se
    sobrar problema depois da correção; senão devolve o input pronto
    pra uso."""
    corrigido = corrigir_tipos_input(entrada, schema)
    problemas = validar_input_schema(corrigido, schema)
    if problemas:
        raise InputInvalido(problemas)
    return corrigido
```

- [x] **Step 4: Run tests to verify they pass**

Run: `pytest ARQUITETURA/nucleo/tests/test_validacao_tool.py -v`
Expected: PASS (8 tests)

- [x] **Step 5: Commit**

```bash
git add ARQUITETURA/nucleo/__init__.py ARQUITETURA/nucleo/validacao_tool.py ARQUITETURA/nucleo/tests/__init__.py ARQUITETURA/nucleo/tests/test_validacao_tool.py
git commit -m "feat: contrato de validacao/reparo de tool input (nucleo v2)"
```

---

### Task 2: `fake_anthropic.py` — test double pra testar loop de tool-calls sem token

**Files:**
- Create: `ARQUITETURA/nucleo/fake_anthropic.py`
- Test: `ARQUITETURA/nucleo/tests/test_fake_anthropic.py`

**Interfaces:**
- Consumes: nada de Task 1 (independente).
- Produces:
  - `fake_tool_use(id: str, name: str, input: dict)` — devolve objeto
    com atributos `.type == "tool_use"`, `.id`, `.name`, `.input`, e
    `.model_dump()` devolvendo o dict equivalente (mesma forma que um
    bloco de conteúdo real do SDK `anthropic`).
  - `fake_text(texto: str)` — devolve objeto com `.type == "text"`,
    `.text`, `.model_dump()`.
  - `fake_response(*blocos)` — devolve objeto com atributo `.content`
    (lista dos blocos passados) — mesma forma que `resposta.content`
    do SDK real.
  - `class ClienteAnthropicFake` — construído com
    `respostas: list[<retorno de fake_response>]` (fila de respostas
    roteirizadas). Expõe `.messages.create(**kwargs)` que: (a) pop da
    fila a próxima resposta roteirizada (levanta `IndexError` com
    mensagem clara se a fila esgotar); (b) ANTES de devolver, valida
    que `kwargs["messages"]` está bem formado — pra cada mensagem
    `role == "assistant"` com blocos `tool_use`, a mensagem seguinte
    (se existir) precisa ter um `tool_result` com `tool_use_id`
    batendo pra CADA `tool_use.id` daquele turno (levanta
    `AssertionError` descrevendo os ids órfãos, se não bater) — essa é
    a verificação que pegou o bug real de tool_use paralelo sem par
    (`AGENTES/julio/orchestrator.py`, sessão de hoje); (c) devolve a
    resposta roteirizada.

- [x] **Step 1: Write the failing tests**

```python
# ARQUITETURA/nucleo/tests/test_fake_anthropic.py
import pytest

from ARQUITETURA.nucleo.fake_anthropic import (
    ClienteAnthropicFake,
    fake_response,
    fake_text,
    fake_tool_use,
)


def test_fake_tool_use_tem_forma_de_bloco_real():
    bloco = fake_tool_use(id="toolu_1", name="minha_tool", input={"x": 1})
    assert bloco.type == "tool_use"
    assert bloco.id == "toolu_1"
    assert bloco.name == "minha_tool"
    assert bloco.input == {"x": 1}
    assert bloco.model_dump()["type"] == "tool_use"


def test_fake_text_tem_forma_de_bloco_real():
    bloco = fake_text("ola")
    assert bloco.type == "text"
    assert bloco.text == "ola"


def test_cliente_fake_devolve_respostas_na_ordem():
    cliente = ClienteAnthropicFake(respostas=[
        fake_response(fake_text("primeira")),
        fake_response(fake_text("segunda")),
    ])
    r1 = cliente.messages.create(messages=[{"role": "user", "content": "oi"}])
    r2 = cliente.messages.create(messages=[{"role": "user", "content": "oi de novo"}])
    assert r1.content[0].text == "primeira"
    assert r2.content[0].text == "segunda"


def test_cliente_fake_levanta_quando_fila_esgota():
    cliente = ClienteAnthropicFake(respostas=[fake_response(fake_text("unica"))])
    cliente.messages.create(messages=[])
    with pytest.raises(IndexError):
        cliente.messages.create(messages=[])


def test_cliente_fake_aceita_historico_bem_formado():
    cliente = ClienteAnthropicFake(respostas=[fake_response(fake_text("ok"))])
    mensagens = [
        {"role": "user", "content": "oi"},
        {"role": "assistant", "content": [
            {"type": "tool_use", "id": "toolu_1", "name": "t", "input": {}},
        ]},
        {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "toolu_1", "content": "ok"},
        ]},
    ]
    cliente.messages.create(messages=mensagens)  # nao deve levantar


def test_cliente_fake_pega_tool_use_paralelo_sem_par():
    """Reproduz o bug real: 2 tool_use no mesmo turno, so 1 tool_result
    pareado -- exatamente o que quebrou em producao (AGENTES/julio/
    orchestrator.py, ver plano de correcao 2026-07-27)."""
    cliente = ClienteAnthropicFake(respostas=[fake_response(fake_text("ok"))])
    mensagens = [
        {"role": "user", "content": "oi"},
        {"role": "assistant", "content": [
            {"type": "tool_use", "id": "toolu_1", "name": "t", "input": {}},
            {"type": "tool_use", "id": "toolu_2", "name": "t", "input": {}},
        ]},
        {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "toolu_1", "content": "ok"},
        ]},
    ]
    with pytest.raises(AssertionError, match="toolu_2"):
        cliente.messages.create(messages=mensagens)
```

- [x] **Step 2: Run tests to verify they fail**

Run: `pytest ARQUITETURA/nucleo/tests/test_fake_anthropic.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ARQUITETURA.nucleo.fake_anthropic'`

- [x] **Step 3: Write minimal implementation**

```python
# ARQUITETURA/nucleo/fake_anthropic.py
"""Test double da API da Anthropic (`anthropic.Anthropic().messages.
create()`), scriptável, sem rede, sem token. Serve pra testar a
mecânica de um loop de tool-calls (pareamento tool_use/tool_result,
tool_use paralelo, retry) contra a MESMA validação que pegaria em
produção -- sem depender de uma decisão real do LLM. Nunca usar em
produção; só em teste.
"""


class _Bloco:
    def __init__(self, tipo: str, **campos):
        self.type = tipo
        for chave, valor in campos.items():
            setattr(self, chave, valor)
        self._campos = campos

    def model_dump(self) -> dict:
        return {"type": self.type, **self._campos}


def fake_tool_use(id: str, name: str, input: dict) -> _Bloco:
    return _Bloco("tool_use", id=id, name=name, input=input)


def fake_text(texto: str) -> _Bloco:
    return _Bloco("text", text=texto)


class _Resposta:
    def __init__(self, content: list[_Bloco]):
        self.content = content


def fake_response(*blocos: _Bloco) -> _Resposta:
    return _Resposta(list(blocos))


def _validar_pareamento_tool_use(mensagens: list[dict]) -> None:
    for i, msg in enumerate(mensagens):
        if msg.get("role") != "assistant" or not isinstance(msg.get("content"), list):
            continue
        ids_tool_use = {
            bloco["id"] for bloco in msg["content"] if isinstance(bloco, dict) and bloco.get("type") == "tool_use"
        }
        if not ids_tool_use:
            continue
        proxima = mensagens[i + 1] if i + 1 < len(mensagens) else {"content": []}
        conteudo_proxima = proxima.get("content", [])
        if not isinstance(conteudo_proxima, list):
            conteudo_proxima = []
        ids_com_resultado = {
            bloco["tool_use_id"] for bloco in conteudo_proxima
            if isinstance(bloco, dict) and bloco.get("type") == "tool_result"
        }
        orfaos = ids_tool_use - ids_com_resultado
        assert not orfaos, f"tool_use sem tool_result pareado: {sorted(orfaos)}"


class _Messages:
    def __init__(self, fila: list[_Resposta]):
        self._fila = fila

    def create(self, **kwargs) -> _Resposta:
        _validar_pareamento_tool_use(kwargs.get("messages", []))
        if not self._fila:
            raise IndexError("ClienteAnthropicFake: fila de respostas roteirizadas esgotou")
        return self._fila.pop(0)


class ClienteAnthropicFake:
    def __init__(self, respostas: list[_Resposta]):
        self.messages = _Messages(list(respostas))
```

- [x] **Step 4: Run tests to verify they pass**

Run: `pytest ARQUITETURA/nucleo/tests/test_fake_anthropic.py -v`
Expected: PASS (6 tests)

- [x] **Step 5: Commit**

```bash
git add ARQUITETURA/nucleo/fake_anthropic.py ARQUITETURA/nucleo/tests/test_fake_anthropic.py
git commit -m "feat: cliente Anthropic fake p/ testar loop de tool-calls sem token (nucleo v2)"
```

---

## Depois deste plano

Essas duas peças não substituem nada em produção sozinhas — são a
fundação que o próximo plano (reescrita do núcleo do agente
conversacional: memória Redis real, canal-agnóstico, execução não-
bloqueante) vai consumir. Só depois que o novo núcleo estiver validado
por esse harness é que faz sentido mover `AGENTES/julio/` pra uma pasta
de referência e promover o código novo a produção — não antes.
