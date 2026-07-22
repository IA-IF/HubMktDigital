# Planejador + Coder v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Duas bibliotecas Python — `REDIS/planejador/` (quebra pedido em tarefas, grava plano no Redis JSON) e `REDIS/coder/` (gera código por tarefa, valida sintaxe, escreve arquivo real dentro do projeto).

**Architecture:** Ambas usam `llm_router` (já existente) pras chamadas de LLM. Planejador produz um plano (`{"pedido", "tarefas": [...]}`) gravado via RedisJSON. Coder consome uma tarefa nesse formato, gera código, valida com `ast.parse`, escreve com guardrail de path (nunca fora da raiz do projeto).

**Tech Stack:** Python, `redis` (módulo RedisJSON/`ReJSON` já confirmado disponível na instância Redis Cloud do projeto), `llm_router` (já commitado), `ast` (stdlib, validação de sintaxe).

## Global Constraints

- Sem suite automatizada — verificação manual (mesmo padrão dos 2 agentes anteriores).
- Coder só escreve dentro de `HubMktDigital/` (raiz do projeto) — nunca nos 3 sites de produção (`C:\INTEGRAFOODS\www\...`), guardrail verificado em código, não só por instrução.
- Validação de sintaxe só pra Python (`ast.parse`) — outras linguagens pulam a validação, sem retry.
- Retry de no máximo 1 tentativa extra (planejador: JSON inválido; coder: sintaxe inválida) — se falhar de novo, propaga o erro (planejador) ou devolve `{"escrito": False, "erro": ...}` (coder), nunca tenta uma terceira vez.
- Credenciais só em `REDIS/.env` (já existe) — nenhuma nova variável necessária, reaproveita tudo do `llm_router`.

---

## Task 1: Planejador

**Files:**
- Create: `REDIS/planejador/__init__.py`
- Create: `REDIS/planejador/planner.py`

**Interfaces:**
- Consumes: `LLMRouter` (de `REDIS/llm_router/router.py`) — `LLMRouter()`, `.ask(prompt, system=None, complexity="complex") -> str`, `.redis_client` (instância `redis.Redis`).
- Produces: classe `Planejador` com `__init__(self)` e `planejar(self, pedido: str) -> dict`, retornando `{"plano_id": str, "pedido": str, "tarefas": [{"id": int, "descricao": str, "arquivo": str, "status": "pendente"}, ...]}`.

- [ ] **Step 1: Criar `REDIS/planejador/__init__.py` vazio**

- [ ] **Step 2: Criar `REDIS/planejador/planner.py`**

```python
"""Planejador: quebra um pedido em texto numa lista ordenada de tarefas,
gravada no Redis (RedisJSON) pro Coder consumir.
"""
import json
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "llm_router"))
from router import LLMRouter  # noqa: E402

SYSTEM_PROMPT = (
    "Voce e um planejador de tarefas de programacao. Dado um pedido, "
    "quebre em uma lista ordenada de tarefas pequenas e objetivas. "
    "Responda APENAS com JSON valido: uma lista de objetos com os campos "
    '"descricao" (string, o que fazer) e "arquivo" (string, caminho '
    "relativo do arquivo a criar ou alterar). Nao inclua nenhum texto "
    "fora do JSON, nem marcacao de bloco de codigo (```)."
)


class Planejador:
    def __init__(self):
        self.router = LLMRouter()

    def planejar(self, pedido: str) -> dict:
        resposta = self.router.ask(
            pedido, system=SYSTEM_PROMPT, complexity="complex"
        )
        tarefas_brutas = self._parsear_com_retry(pedido, resposta)

        tarefas = [
            {
                "id": i + 1,
                "descricao": t["descricao"],
                "arquivo": t["arquivo"],
                "status": "pendente",
            }
            for i, t in enumerate(tarefas_brutas)
        ]
        plano_id = str(uuid.uuid4())
        plano = {"pedido": pedido, "tarefas": tarefas}

        self.router.redis_client.json().set(f"plan:{plano_id}", "$", plano)

        return {"plano_id": plano_id, **plano}

    def _parsear_com_retry(self, pedido: str, resposta: str) -> list[dict]:
        try:
            return json.loads(resposta)
        except json.JSONDecodeError as e:
            pedido_correcao = (
                f"{pedido}\n\nSua resposta anterior nao era JSON valido "
                f"(erro: {e}). Responda de novo, APENAS com o JSON, sem "
                "texto extra nem marcacao de bloco de codigo."
            )
            resposta2 = self.router.ask(
                pedido_correcao, system=SYSTEM_PROMPT, complexity="complex"
            )
            return json.loads(resposta2)
```

- [ ] **Step 3: Verificar manualmente — plano real gravado no Redis**

Run (de dentro de `REDIS/planejador/`):
```
python -c "
from planner import Planejador
p = Planejador()
resultado = p.planejar('Crie um script Python simples que imprime a tabuada do 7.')
print('plano_id:', resultado['plano_id'])
for t in resultado['tarefas']:
    print(t)

# confere que ficou gravado no Redis de verdade
gravado = p.router.redis_client.json().get(f\"plan:{resultado['plano_id']}\")
print('Gravado no Redis:', gravado is not None)
print('Bate com o retornado:', gravado['tarefas'] == resultado['tarefas'])
"
```
Expected: imprime `Connected to Redis successfully`, `Connected to LLM successfully` (essas duas vêm do `LLMRouter`/conectividade — se não aparecerem, confira se `LLMRouter.__init__` as imprime; se não imprimir por design do router, ignore essa linha do Expected e confirme só o restante), pelo menos 1 tarefa com `descricao`/`arquivo` fazendo sentido pro pedido, `Gravado no Redis: True`, `Bate com o retornado: True`.

- [ ] **Step 4: Commit**

```bash
git add REDIS/planejador/__init__.py REDIS/planejador/planner.py
git commit -m "Adiciona planejador (quebra pedido em tarefas, grava no Redis)"
```

---

## Task 2: Coder

**Files:**
- Create: `REDIS/coder/__init__.py`
- Create: `REDIS/coder/coder.py`

**Interfaces:**
- Consumes: `LLMRouter` (mesma interface da Task 1) e o formato de tarefa produzido pelo Planejador (`{"descricao": str, "arquivo": str, ...}` — usa só esses 2 campos, ignora os outros).
- Produces: classe `Coder` com `__init__(self)` e `implementar(self, tarefa: dict) -> dict`, retornando `{"arquivo": str, "escrito": bool, "erro": str | None}`.

- [ ] **Step 1: Criar `REDIS/coder/__init__.py` vazio**

- [ ] **Step 2: Criar `REDIS/coder/coder.py`**

```python
"""Coder: gera codigo Python pra uma tarefa, valida sintaxe antes de
escrever, escreve so dentro da raiz deste projeto (nunca nos sites de
producao — guardrail verificado em codigo).
"""
import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "llm_router"))
from router import LLMRouter  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

SYSTEM_PROMPT = (
    "Voce e um agente que escreve codigo Python. Dada uma descricao de "
    "tarefa, responda APENAS com o codigo Python completo do arquivo, "
    "pronto pra salvar direto. Sem explicacao, sem markdown, sem cercas "
    "de bloco de codigo (```)."
)


class Coder:
    def __init__(self):
        self.router = LLMRouter()

    def implementar(self, tarefa: dict) -> dict:
        arquivo_relativo = tarefa["arquivo"]
        caminho = (REPO_ROOT / arquivo_relativo).resolve()

        try:
            caminho.relative_to(REPO_ROOT)
        except ValueError:
            return {
                "arquivo": arquivo_relativo,
                "escrito": False,
                "erro": f"arquivo fora da raiz do projeto: {arquivo_relativo}",
            }

        codigo = self._gerar_codigo(tarefa["descricao"])
        valido, erro = self._validar_sintaxe(codigo)

        if not valido:
            codigo = self._gerar_codigo(
                f"{tarefa['descricao']}\n\nSeu codigo anterior tinha um "
                f"erro de sintaxe: {erro}\nGere o arquivo completo de "
                "novo, corrigido."
            )
            valido, erro = self._validar_sintaxe(codigo)

        if not valido:
            return {"arquivo": arquivo_relativo, "escrito": False, "erro": erro}

        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_text(codigo, encoding="utf-8")
        return {"arquivo": arquivo_relativo, "escrito": True, "erro": None}

    def _gerar_codigo(self, descricao: str) -> str:
        return self.router.ask(
            descricao, system=SYSTEM_PROMPT, complexity="complex"
        )

    @staticmethod
    def _validar_sintaxe(codigo: str) -> tuple[bool, str | None]:
        try:
            ast.parse(codigo)
            return True, None
        except SyntaxError as e:
            return False, str(e)
```

- [ ] **Step 3: Verificar manualmente — arquivo real escrito e sintaticamente valido**

Run (de dentro de `REDIS/coder/`):
```
python -c "
from coder import Coder
c = Coder()
tarefa = {
    'descricao': 'Crie um script Python simples que imprime a tabuada do 7, de 1 a 10.',
    'arquivo': 'REDIS/coder/_teste_tabuada.py',
}
resultado = c.implementar(tarefa)
print(resultado)
"
```
Expected: `{'arquivo': 'REDIS/coder/_teste_tabuada.py', 'escrito': True, 'erro': None}`.

Depois, confirme que o arquivo existe e roda de verdade:
```
python REDIS/coder/_teste_tabuada.py
```
Expected: imprime a tabuada do 7 (`7 x 1 = 7` até `7 x 10 = 70`, ou formato parecido — o importante é rodar sem `SyntaxError`/traceback).

Também teste o guardrail de path (não deve escrever nada fora do projeto):
```
python -c "
from coder import Coder
c = Coder()
tarefa = {'descricao': 'qualquer coisa', 'arquivo': '../../../windows/system32/teste.py'}
print(c.implementar(tarefa))
"
```
Expected: `{'arquivo': '../../../windows/system32/teste.py', 'escrito': False, 'erro': 'arquivo fora da raiz do projeto: ../../../windows/system32/teste.py'}`.

Por fim, apague o arquivo de teste gerado (não faz parte do produto, é só verificação):
```
rm REDIS/coder/_teste_tabuada.py
```

- [ ] **Step 4: Commit**

```bash
git add REDIS/coder/__init__.py REDIS/coder/coder.py
git commit -m "Adiciona coder (gera codigo, valida sintaxe, escreve dentro do projeto)"
```

---

## Self-Review (preenchido ao escrever o plano)

**Spec coverage:**
- Planejador: pedido → JSON de tarefas → grava no Redis (RedisJSON) → Task 1
- Retry de JSON inválido (1 tentativa extra) → Task 1, `_parsear_com_retry`
- Coder: tarefa → código → valida sintaxe → escreve arquivo real → Task 2
- Retry de sintaxe inválida (1 tentativa extra) → Task 2, `implementar`
- Guardrail de path (nunca escreve fora da raiz do projeto) → Task 2, `implementar` (checagem com `relative_to`) + testado explicitamente no Step 3
- Ambos usando `llm_router` (nunca SDK Anthropic direto) → Task 1 e 2, `sys.path.insert` + `from router import LLMRouter`
- Fora de escopo (sites de produção, agente de teste, validação multi-linguagem, orquestração automática de plano completo) → nenhuma task toca nisso

**Placeholder scan:** nenhum "TBD"/"TODO" — código completo em toda etapa.

**Type consistency:** `Planejador.planejar(pedido: str) -> dict` retorna `tarefas` no formato `{"id", "descricao", "arquivo", "status"}` — `Coder.implementar(tarefa: dict) -> dict` (Task 2) só lê `tarefa["descricao"]` e `tarefa["arquivo"]`, que existem nesse formato (os campos extras `id`/`status` são ignorados, sem problema). `LLMRouter.ask(prompt, system=None, complexity="complex")` é chamado com a mesma assinatura nas duas tasks.
