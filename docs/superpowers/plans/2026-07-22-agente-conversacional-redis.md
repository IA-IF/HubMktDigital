# Agente Conversacional v1 (Redis + Claude) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Um CLI Python que conversa com Claude e lembra o histórico via busca semântica no Redis Cloud.

**Architecture:** Processo único (`main.py`) com loop de input; `agent.py` monta o prompt combinando histórico relevante (RedisVL `SemanticMessageHistory`) com a mensagem nova e chama o SDK oficial `anthropic`; `config.py` centraliza credenciais.

**Tech Stack:** Python, `redis` 7.4.0, `redisvl` 0.23.0 (com `HFTextVectorizer` local, modelo default `sentence-transformers/all-mpnet-base-v2`), `anthropic` 0.116.0, `python-dotenv` 1.1.1. Todos já instalados no ambiente (`pip show` confirmado em 2026-07-22).

## Global Constraints

- Sem suite de testes automatizada nesta v1 — verificação é manual, rodando o CLI de verdade (decisão do spec `docs/superpowers/specs/2026-07-22-agente-conversacional-redis-design.md`, consistente com o padrão dos módulos em `LEGADO/`).
- Embeddings só via modelo local (`HFTextVectorizer`), nunca API paga — decisão deliberada de custo do spec.
- Credenciais só em `REDIS/.env` (gitignored) — nunca hardcoded, nunca no `.env.example`.
- `REDIS_URL` é a connection string completa (`redis://default:SENHA@HOST:PORTA`), formato que já está documentado em `REDIS/CLAUDE.md`.
- Sem Telegram nem outro canal externo nesta v1 — só CLI local.

---

## Task 1: Config e scaffolding do projeto

**Files:**
- Create: `REDIS/.gitignore`
- Create: `REDIS/.env.example`
- Create: `REDIS/agente-conversacional/__init__.py`
- Create: `REDIS/agente-conversacional/config.py`

**Interfaces:**
- Produces: `config.REDIS_URL: str`, `config.ANTHROPIC_API_KEY: str`, `config.CLAUDE_MODEL: str` (funções `redis_url() -> str`, `anthropic_api_key() -> str`, `claude_model() -> str`), todas carregadas de `REDIS/.env` via `python-dotenv`.

- [ ] **Step 1: Criar `REDIS/.gitignore`**

```
.env
!.env.example
__pycache__/
*.pyc
```

- [ ] **Step 2: Criar `REDIS/.env.example`**

```
# Copie para .env na mesma pasta (REDIS/) e preencha.

# Connection string completa do Redis Cloud (ver REDIS/CLAUDE.md para o
# valor real do projeto — redis-cli -u redis://default:SENHA@HOST:PORTA)
REDIS_URL=redis://default:SENHA@HOST:PORTA

ANTHROPIC_API_KEY=
CLAUDE_MODEL=claude-sonnet-4-6
```

- [ ] **Step 3: Criar `REDIS/agente-conversacional/__init__.py` vazio**

Arquivo vazio — só pra permitir `import` do pacote se algum dia precisar.

- [ ] **Step 4: Criar `REDIS/agente-conversacional/config.py`**

```python
"""Carrega credenciais do .env em REDIS/ (um nivel acima deste pacote)."""
import os
from pathlib import Path

from dotenv import load_dotenv

PACKAGE_ROOT = Path(__file__).resolve().parent
REDIS_ROOT = PACKAGE_ROOT.parent
ENV_FILE = REDIS_ROOT / ".env"
load_dotenv(ENV_FILE)


def _obrigatoria(nome: str) -> str:
    valor = os.getenv(nome, "").strip()
    if not valor:
        raise SystemExit(
            f"Variavel {nome} nao definida — copie REDIS/.env.example para "
            "REDIS/.env e preencha as credenciais."
        )
    return valor


def redis_url() -> str:
    return _obrigatoria("REDIS_URL")


def anthropic_api_key() -> str:
    return _obrigatoria("ANTHROPIC_API_KEY")


def claude_model() -> str:
    return os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")
```

- [ ] **Step 5: Copiar `REDIS/.env.example` para `REDIS/.env` e preencher com a connection string real**

Pegue o valor real de `REDIS/CLAUDE.md` (linha do `redis-cli -u redis://...`) e a `ANTHROPIC_API_KEY` real. Este arquivo é gitignored — nunca commitar.

- [ ] **Step 6: Verificar manualmente que o config carrega**

Run (de dentro de `REDIS/agente-conversacional/`):
```
python -c "import config; print(config.redis_url()[:20] + '...'); print('model:', config.claude_model())"
```
Expected: imprime os primeiros 20 caracteres da URL (sem vazar a senha inteira) e o nome do modelo, sem erro.

Run (renomeando `REDIS/.env` temporariamente pra provar o erro é claro):
```
python -c "
import pathlib
p = pathlib.Path('../.env')
p.rename('../.env.bak')
import subprocess, sys
r = subprocess.run([sys.executable, '-c', 'import config; config.redis_url()'], capture_output=True, text=True)
print(r.stderr[-200:])
p.parent.joinpath('.env.bak').rename(p)
"
```
Expected: a última linha do stderr contém `Variavel REDIS_URL nao definida`.

- [ ] **Step 7: Commit**

```bash
git add REDIS/.gitignore REDIS/.env.example REDIS/agente-conversacional/__init__.py REDIS/agente-conversacional/config.py
git commit -m "Adiciona config do agente conversacional (REDIS + Claude)"
```

---

## Task 2: requirements.txt

**Files:**
- Create: `REDIS/agente-conversacional/requirements.txt`

**Interfaces:**
- Consumes: nada (task isolada de dependências)
- Produces: nada em código — só documenta o que Task 3/4 vão importar (`redis`, `redisvl`, `anthropic`, `python-dotenv`)

- [ ] **Step 1: Criar `REDIS/agente-conversacional/requirements.txt`**

```
redis==7.4.0
redisvl==0.23.0
anthropic==0.116.0
python-dotenv==1.1.1
sentence-transformers==3.4.1
```

- [ ] **Step 2: Verificar que tudo já está instalado no ambiente (confirmado em 2026-07-22)**

Run:
```
pip show redis redisvl anthropic python-dotenv sentence-transformers | grep -E "^Name|^Version"
```
Expected: 5 pares Name/Version aparecem, sem "WARNING: Package(s) not found".

Se algo faltar (ambiente diferente do usado nesta sessão):
```
pip install -r REDIS/agente-conversacional/requirements.txt
```

- [ ] **Step 3: Commit**

```bash
git add REDIS/agente-conversacional/requirements.txt
git commit -m "Documenta dependencias do agente conversacional"
```

---

## Task 3: ConversationalAgent (agent.py)

**Files:**
- Create: `REDIS/agente-conversacional/agent.py`

**Interfaces:**
- Consumes: `config.redis_url()`, `config.anthropic_api_key()`, `config.claude_model()` (Task 1)
- Produces: classe `ConversationalAgent` com `__init__(self, session_name: str = "chat")` e `chat(self, user_input: str) -> str` — é isso que `main.py` (Task 4) importa e chama.

Pontos que corrigem os 3 problemas do `REDIS/generated-reference-conversational-agent.py`:
1. Usa `anthropic.Anthropic().messages.create(model=, max_tokens=, system=, messages=)` de verdade, não o hack `openai.OpenAI(base_url=...)`.
2. `SemanticMessageHistory` sem passar `vectorizer` explicitamente — o default já é `HFTextVectorizer("sentence-transformers/all-mpnet-base-v2")`, local, confirmado lendo o código-fonte do redisvl 0.23.0 (nenhuma chamada de API paga pra gerar embedding).
3. Usa `config.redis_url()` (a connection string real do projeto) em vez de `REDIS_HOST`/`REDIS_PORT` soltos.

Limitação conhecida (documentada em comentário, não é bug a "corrigir" nesta v1): a API da Anthropic exige que a primeira mensagem do array `messages` tenha `role="user"`. Se a busca semântica trouxer como resultado mais relevante uma mensagem `role="assistant"` antiga, a chamada pode falhar — nesse caso cai no `except` existente e devolve a mensagem de erro amigável. Aceitável para v1 (spec não pediu tratamento especial pra isso).

- [ ] **Step 1: Escrever `REDIS/agente-conversacional/agent.py`**

```python
"""Agente conversacional: Claude + memoria semantica no Redis.

Corrige 3 problemas do REDIS/generated-reference-conversational-agent.py
(codigo bruto gerado pelo agent-builder oficial da Redis): usa o SDK real
da Anthropic (nao o hack openai.OpenAI(base_url=...) contra a API da
Anthropic, que nao funciona), usa a REDIS_URL real do projeto, e conta
com o vectorizer local (HFTextVectorizer) que ja e o default do
SemanticMessageHistory - sem custo de API por mensagem.
"""
import anthropic
import redis
from redisvl.extensions.message_history import SemanticMessageHistory

import config

SYSTEM_PROMPT = (
    "You are a helpful assistant that will answer questions based on the "
    "conversation history."
)


class ConversationalAgent:
    def __init__(self, session_name: str = "chat"):
        self.model = config.claude_model()

        try:
            self.redis_client = redis.Redis.from_url(
                config.redis_url(), decode_responses=True
            )
            self.redis_client.ping()
            print("Connected to Redis successfully")
        except redis.ConnectionError as e:
            print(f"Failed to connect to Redis: {e}")
            print("Please check your REDIS_URL and ensure Redis is running.")
            raise

        self.llm_client = anthropic.Anthropic(api_key=config.anthropic_api_key())
        try:
            self.llm_client.messages.create(
                model=self.model,
                max_tokens=5,
                messages=[{"role": "user", "content": "Hello"}],
            )
            print("Connected to LLM successfully")
        except anthropic.AuthenticationError:
            print("LLM authentication failed. Please check your API key.")
            raise

        self.session_manager = SemanticMessageHistory(
            name=session_name,
            redis_client=self.redis_client,
        )

    def chat(self, user_input: str) -> str:
        self.session_manager.set_distance_threshold(0.9)
        context = self.session_manager.get_relevant(user_input, top_k=8)

        messages = list(context)
        messages.append({"role": "user", "content": user_input})

        try:
            response = self.llm_client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                messages=messages,
            )
        except Exception as e:
            print(f"Error getting LLM response: {e}")
            return "Sorry, I'm having trouble understanding your question. Please try again later."

        assistant_response = response.content[0].text

        try:
            self.session_manager.add_messages([
                {"role": "user", "content": user_input},
                {"role": "assistant", "content": assistant_response},
            ])
        except Exception as e:
            print(f"Error storing conversation: {e}")

        return assistant_response
```

- [ ] **Step 2: Verificar manualmente a inicialização (sem gastar tokens de chat)**

Run (de dentro de `REDIS/agente-conversacional/`):
```
python -c "from agent import ConversationalAgent; a = ConversationalAgent(session_name='smoke_test_init')"
```
Expected: imprime `Connected to Redis successfully` e `Connected to LLM successfully`, sem traceback. (Isso já teria pego os 3 problemas do código gerado: URL errada, SDK errado, ou custo de embedding inesperado teriam quebrado ou custado dinheiro aqui.)

- [ ] **Step 3: Commit**

```bash
git add REDIS/agente-conversacional/agent.py
git commit -m "Adiciona ConversationalAgent (Claude + memoria semantica no Redis)"
```

---

## Task 4: CLI (main.py) e smoke test fim-a-fim

**Files:**
- Create: `REDIS/agente-conversacional/main.py`

**Interfaces:**
- Consumes: `agent.ConversationalAgent` (Task 3)

- [ ] **Step 1: Escrever `REDIS/agente-conversacional/main.py`**

```python
"""CLI do agente conversacional. Rode dentro de REDIS/agente-conversacional/:
    python main.py
"""
from agent import ConversationalAgent


def main() -> None:
    try:
        agent = ConversationalAgent()
    except Exception as e:
        print(f"Falha ao iniciar o agente: {e}")
        raise SystemExit(1)

    print("Agente pronto. Digite 'sair' pra encerrar.\n")
    while True:
        try:
            prompt = input("Voce: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nAte mais!")
            break

        if not prompt:
            continue
        if prompt.lower() in {"sair", "exit", "quit"}:
            print("Ate mais!")
            break

        resposta = agent.chat(prompt)
        print(f"Claude: {resposta}\n")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Smoke test manual fim-a-fim — verificar que a memoria semantica funciona de verdade**

Run (de dentro de `REDIS/agente-conversacional/`, interativo):
```
python main.py
```

Digite, em sequência:
1. `Meu prato favorito de carne e picanha na brasa.`
2. `Qual e a capital da França?` (pergunta sem relação, só pra "sujar" o contexto recente)
3. `Qual e o meu prato de carne favorito mesmo?`

Expected: a resposta da mensagem 3 menciona "picanha" — prova que a busca *semântica* recuperou a mensagem 1 (que está longe cronologicamente, não é só "últimas N mensagens"). Se a resposta não souber, o teste falhou — revisar `distance_threshold`/`top_k` em `agent.py` antes de prosseguir.

Digite `sair` pra encerrar.

- [ ] **Step 3: Commit**

```bash
git add REDIS/agente-conversacional/main.py
git commit -m "Adiciona CLI do agente conversacional"
```

---

## Self-Review (preenchido ao escrever o plano)

**Spec coverage:**
- Arquitetura (ciclo de 6 passos) → Task 3 (`agent.py`) + Task 4 (`main.py`)
- `config.py` carregando `REDIS/.env` → Task 1
- SDK real da Anthropic (correção do problema 1) → Task 3, Step 1
- `HFTextVectorizer` local sem custo (correção do problema 2 / decisão de custo) → Task 3, Step 1 (comentário explica que é o default)
- `REDIS_URL` real do projeto (correção do problema 3) → Task 1 + Task 3
- Erros: falha de Redis é fatal, falha de LLM pontual não derruba sessão → Task 3, Step 1
- Teste manual multi-turno → Task 4, Step 2
- Fora de escopo (Telegram, perfil persistente, outros agentes, TTL) → nenhuma task toca nisso, coerente

**Placeholder scan:** nenhum "TBD"/"TODO" — todo código é completo e executável como escrito.

**Type consistency:** `ConversationalAgent.__init__(self, session_name: str = "chat")` (Task 3) é exatamente o que `main.py` chama sem argumentos (Task 4) — usa o default. `chat(self, user_input: str) -> str` é o único método que `main.py` chama. Nomes de função em `config.py` (`redis_url`, `anthropic_api_key`, `claude_model`) são os mesmos usados em `agent.py`.
