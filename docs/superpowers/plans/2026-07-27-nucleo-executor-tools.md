# Núcleo v2 — executor de tools reais (TOOLS/**/tool.json) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generalizar o despacho de tools reais catalogadas em
`TOOLS/**/tool.json` (hoje feito em `AGENTES/julio/agentes.py`:
`rodar_tool`/`criar_campanha_ads`) numa fábrica de `ExecutorTool` (Plano
2) que fala o vocabulário de falha do núcleo novo —
`FalhaPermanente`/`FalhaTransitoria` — em vez de `RuntimeError`
genérico. Isso é o que falta pra `processar_turno` do Plano 2 poder
rodar tools de verdade em vez de callbacks de teste.

**Architecture:** `criar_executor_tool(hub_root, tool_por_nome, site)`
devolve uma função `(nome_tool, entrada) -> resultado` que roda o
script real via subprocess (mesma mecânica de `agentes.py`: `argv` ou
`stdin` conforme `modo_entrada`), e classifica a falha: resposta válida
`{"ok": false, "erros": [...]}` → `FalhaPermanente` (problema no input,
não adianta retry as-is); saída que não é JSON válido (script
quebrou/dependência faltando) → `FalhaTransitoria` (pode ser
transitório, retry faz sentido). Testado com scripts Python reais
escritos em `tmp_path` — subprocess de verdade, sem depender de
credencial nenhuma do Google.

**Tech Stack:** Python 3.11+, `pytest` (`tmp_path` fixture).

## Global Constraints

- Não mexe em `AGENTES/julio/`, `TOOLS/`, `LEGADO/`.
- Testes usam scripts Python reais escritos em `tmp_path` (subprocess
  de verdade) — nunca chamam uma API do Google de verdade.

---

## File Structure

- Create: `ARQUITETURA/nucleo/executor_tools.py`
- Create: `ARQUITETURA/nucleo/tests/test_executor_tools.py`

---

### Task 1: `criar_executor_tool` — despacho genérico com classificação de falha

**Files:**
- Create: `ARQUITETURA/nucleo/executor_tools.py`
- Test: `ARQUITETURA/nucleo/tests/test_executor_tools.py`

**Interfaces:**
- Consumes: `FalhaPermanente`, `FalhaTransitoria` (de
  `ARQUITETURA.nucleo.agente`, Plano 2).
- Produces:
  - `criar_executor_tool(hub_root: Path, tool_por_nome: dict[str, dict], site: str) -> ExecutorTool` —
    `tool_por_nome` mapeia `name -> tool.json` (dict com `script`,
    `modo_entrada`, `input_schema`). O `ExecutorTool` devolvido:
    - modo `"argv"`: roda `python <script> <site> <valores das
      propriedades do input_schema, na ordem, ate a 1a ausente>`.
    - modo `"stdin"`: roda `python <script> <site>` com `entrada`
      serializada em JSON no stdin.
    - saída do script parseada como JSON: se `resposta.get("ok") is False`
      e `"erros" in resposta` → `raise FalhaPermanente("; ".join(erros))`;
      senão devolve `resposta`.
    - saída que não é JSON válido → `raise FalhaTransitoria(<detalhe
      tecnico com stdout/stderr/codigo de saida>)`.
    - `nome_tool` ausente em `tool_por_nome` → `raise
      FalhaPermanente(f"ferramenta desconhecida: {nome_tool}")`.

- [ ] **Step 1: Write the failing tests**

```python
# ARQUITETURA/nucleo/tests/test_executor_tools.py
import json
import textwrap

import pytest

from ARQUITETURA.nucleo.agente import FalhaPermanente, FalhaTransitoria
from ARQUITETURA.nucleo.executor_tools import criar_executor_tool


def _escrever_script(tmp_path, nome: str, codigo: str):
    caminho = tmp_path / nome
    caminho.write_text(textwrap.dedent(codigo), encoding="utf-8")
    return caminho


def test_executor_roda_tool_modo_argv_e_devolve_resultado(tmp_path):
    script = _escrever_script(tmp_path, "echo_argv.py", """
        import json, sys
        site = sys.argv[1]
        valor = sys.argv[2] if len(sys.argv) > 2 else None
        print(json.dumps({"site": site, "valor": valor}))
    """)
    tool_por_nome = {
        "minha_tool": {
            "script": "echo_argv.py",
            "modo_entrada": "argv",
            "input_schema": {"properties": {"valor": {"type": "string"}}},
        }
    }
    executar = criar_executor_tool(tmp_path, tool_por_nome, "3gfoods")
    resultado = executar("minha_tool", {"valor": "abc"})
    assert resultado == {"site": "3gfoods", "valor": "abc"}


def test_executor_roda_tool_modo_stdin_e_devolve_resultado(tmp_path):
    script = _escrever_script(tmp_path, "echo_stdin.py", """
        import json, sys
        entrada = json.load(sys.stdin)
        print(json.dumps({"recebido": entrada, "site": sys.argv[1]}))
    """)
    tool_por_nome = {
        "cria_campanha": {
            "script": "echo_stdin.py",
            "modo_entrada": "stdin",
            "input_schema": {"properties": {}},
        }
    }
    executar = criar_executor_tool(tmp_path, tool_por_nome, "adoro")
    resultado = executar("cria_campanha", {"nome": "X"})
    assert resultado == {"recebido": {"nome": "X"}, "site": "adoro"}


def test_executor_levanta_falha_permanente_quando_ok_false_com_erros(tmp_path):
    script = _escrever_script(tmp_path, "falha_validacao.py", """
        import json
        print(json.dumps({"ok": False, "erros": ["titulo excede 30 caracteres"]}))
    """)
    tool_por_nome = {"t": {"script": "falha_validacao.py", "modo_entrada": "argv", "input_schema": {"properties": {}}}}
    executar = criar_executor_tool(tmp_path, tool_por_nome, "3gfoods")
    with pytest.raises(FalhaPermanente, match="titulo excede 30 caracteres"):
        executar("t", {})


def test_executor_levanta_falha_transitoria_quando_saida_nao_e_json(tmp_path):
    script = _escrever_script(tmp_path, "quebra.py", """
        raise ModuleNotFoundError("No module named 'google'")
    """)
    tool_por_nome = {"t": {"script": "quebra.py", "modo_entrada": "argv", "input_schema": {"properties": {}}}}
    executar = criar_executor_tool(tmp_path, tool_por_nome, "3gfoods")
    with pytest.raises(FalhaTransitoria):
        executar("t", {})


def test_executor_levanta_falha_permanente_pra_tool_desconhecida(tmp_path):
    executar = criar_executor_tool(tmp_path, {}, "3gfoods")
    with pytest.raises(FalhaPermanente, match="desconhecida"):
        executar("nao_existe", {})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest ARQUITETURA/nucleo/tests/test_executor_tools.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ARQUITETURA.nucleo.executor_tools'`

- [ ] **Step 3: Write minimal implementation**

```python
# ARQUITETURA/nucleo/executor_tools.py
"""Despacho de tools reais catalogadas em TOOLS/**/tool.json --
generaliza AGENTES/julio/agentes.py (rodar_tool/criar_campanha_ads)
falando o vocabulario de falha do nucleo v2 (FalhaPermanente vs
FalhaTransitoria) em vez de RuntimeError generico.
"""
import json
import subprocess
import sys
from pathlib import Path

from ARQUITETURA.nucleo.agente import ExecutorTool, FalhaPermanente, FalhaTransitoria


def _rodar_subprocess(script: Path, argv: list[str], entrada_stdin: str | None = None) -> dict:
    resultado = subprocess.run(
        [sys.executable, str(script), *argv],
        input=entrada_stdin, capture_output=True, text=True, encoding="utf-8",
    )
    saida = (resultado.stdout or "").strip()
    try:
        return json.loads(saida)
    except json.JSONDecodeError:
        raise FalhaTransitoria(
            f"{script.name} nao retornou JSON valido (codigo {resultado.returncode}): "
            f"{resultado.stdout}\n{resultado.stderr}"
        )


def criar_executor_tool(hub_root: Path, tool_por_nome: dict[str, dict], site: str) -> ExecutorTool:
    def executar(nome_tool: str, entrada: dict) -> dict:
        tool = tool_por_nome.get(nome_tool)
        if tool is None:
            raise FalhaPermanente(f"ferramenta desconhecida: {nome_tool}")

        script = hub_root / tool["script"]
        modo = tool.get("modo_entrada", "argv")

        if modo == "stdin":
            resposta = _rodar_subprocess(script, [site], entrada_stdin=json.dumps(entrada, ensure_ascii=False))
        else:
            argv = [site]
            for chave in tool["input_schema"]["properties"]:
                if chave not in entrada or entrada[chave] is None:
                    break
                valor = entrada[chave]
                argv.append(",".join(valor) if isinstance(valor, list) else str(valor))
            resposta = _rodar_subprocess(script, argv)

        if resposta.get("ok") is False and "erros" in resposta:
            raise FalhaPermanente("; ".join(resposta["erros"]))
        return resposta

    return executar
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest ARQUITETURA/nucleo/tests/test_executor_tools.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add ARQUITETURA/nucleo/executor_tools.py ARQUITETURA/nucleo/tests/test_executor_tools.py
git commit -m "feat: criar_executor_tool - despacho de tools reais com FalhaPermanente/Transitoria (nucleo v2)"
```

---

## Depois deste plano

Falta: `canal_telegram.py` (Canal real via Telegram Bot API) e um
`main.py` de assembly ligando `DespachanteConcorrente` +
`RepositorioEstadoRedis` + `criar_executor_tool` + `Canal` real —
ambos mais integração/smoke-test do que unidade pura, então ficam pra
uma sessão com acesso a credenciais reais pra validar de ponta a ponta.
Depois disso, a otimização de cada TOOLS/* contra a doc oficial de cada
API continua sendo o maior ponto em aberto (ponto 1 do
`entendimento.md`).
