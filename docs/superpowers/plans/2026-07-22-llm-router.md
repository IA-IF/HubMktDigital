# Otimizador de custo de LLM v1 (llm_router) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Biblioteca Python (`REDIS/llm_router/`) com cache semântico + roteamento de modelo, integrada ao agente conversacional já existente.

**Architecture:** `LLMRouter` conecta Redis + Anthropic uma vez; `ask()` cacheia (SemanticCache por tier) e roteia por complexidade; `ask_with_history()` só roteia (sem cache, histórico varia). `agente-conversacional/agent.py` passa a usar as duas em vez do SDK Anthropic direto.

**Tech Stack:** Python, `redis`, `redisvl` (`SemanticCache` de `redisvl.extensions.cache.llm`, default vectorizer local `HFTextVectorizer`), `anthropic`, `python-dotenv` — todos já instalados (mesmas versões do agente conversacional).

## Global Constraints

- Sem suite automatizada nesta v1 — verificação manual (mesmo padrão do agente conversacional).
- Sem TTL no cache nesta v1.
- `complexity` é sempre `"simple"` ou `"complex"` — quem chama decide, sem heurística automática.
- `ask()` é cacheado (perguntas isoladas); `ask_with_history()` NUNCA usa cache (histórico varia por chamada — cachear geraria resposta errada pra outro usuário/sessão).
- Duas instâncias de `SemanticCache` (uma por tier), nunca uma resposta "simple" devolvida quando pediram "complex" ou vice-versa.
- Credenciais só em `REDIS/.env` (já existe, gitignored) — reaproveitar `REDIS_URL`/`ANTHROPIC_API_KEY`, não duplicar.

---

## Task 1: Biblioteca llm_router (config.py + router.py)

**Files:**
- Create: `REDIS/llm_router/__init__.py`
- Create: `REDIS/llm_router/config.py`
- Create: `REDIS/llm_router/router.py`

**Interfaces:**
- Produces: `config.redis_url()`, `config.anthropic_api_key()`, `config.simple_model()`, `config.complex_model()`.
- Produces: classe `LLMRouter` com `__init__(self)`, atributo público `self.redis_client` (instância `redis.Redis`, reutilizável por quem integrar), `ask(self, prompt: str, system: str | None = None, complexity: str = "complex") -> str`, `ask_with_history(self, messages: list[dict], system: str | None = None, complexity: str = "complex") -> str`.

- [ ] **Step 1: Criar `REDIS/llm_router/__init__.py` vazio**

- [ ] **Step 2: Criar `REDIS/llm_router/config.py`**

```python
"""Carrega credenciais do .env compartilhado em REDIS/ (um nivel acima)."""
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
            f"Variavel {nome} nao definida — confira REDIS/.env "
            "(copie de REDIS/.env.example se ainda nao existir)."
        )
    return valor


def redis_url() -> str:
    return _obrigatoria("REDIS_URL")


def anthropic_api_key() -> str:
    return _obrigatoria("ANTHROPIC_API_KEY")


def simple_model() -> str:
    return os.getenv("LLM_ROUTER_SIMPLE_MODEL", "claude-haiku-4-5-20251001")


def complex_model() -> str:
    return os.getenv("LLM_ROUTER_COMPLEX_MODEL", "claude-sonnet-4-6")
```

- [ ] **Step 3: Criar `REDIS/llm_router/router.py`**

```python
"""Roteador de custo de LLM: cache semantico (Redis) + escolha de modelo.

Duas portas de entrada, deliberadamente diferentes:
- ask(): cacheada, para perguntas isoladas onde a mesma pergunta sempre
  tem a mesma resposta certa (ex: FAQ, teste de conectividade).
- ask_with_history(): so roteada, NUNCA cacheada — o resultado depende do
  historico passado em `messages`, que varia a cada chamada; cachear por
  similaridade de prompt devolveria a resposta de outra conversa/usuario.
"""
import anthropic
import redis
from redisvl.extensions.cache.llm import SemanticCache

import config

_COMPLEXITIES = ("simple", "complex")


def _validar_complexity(complexity: str) -> str:
    if complexity not in _COMPLEXITIES:
        raise ValueError(
            f"complexity invalido: {complexity!r} — use 'simple' ou 'complex'"
        )
    return complexity


class LLMRouter:
    def __init__(self):
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

        self._models = {
            "simple": config.simple_model(),
            "complex": config.complex_model(),
        }
        # Uma instancia de cache por tier: garante que uma resposta gerada
        # pelo modelo barato nunca seja devolvida quando alguem pede o
        # modelo caro, e vice-versa.
        self._caches = {
            "simple": SemanticCache(
                name="llmcache_simple", redis_client=self.redis_client
            ),
            "complex": SemanticCache(
                name="llmcache_complex", redis_client=self.redis_client
            ),
        }

    def _model_for(self, complexity: str) -> str:
        return self._models[_validar_complexity(complexity)]

    def ask(
        self, prompt: str, system: str | None = None, complexity: str = "complex"
    ) -> str:
        complexity = _validar_complexity(complexity)
        cache = self._caches[complexity]

        hits = cache.check(prompt=prompt)
        if hits:
            return hits[0]["response"]

        kwargs = {
            "model": self._model_for(complexity),
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system
        response = self.llm_client.messages.create(**kwargs)
        texto = response.content[0].text

        cache.store(prompt=prompt, response=texto)
        return texto

    def ask_with_history(
        self,
        messages: list[dict],
        system: str | None = None,
        complexity: str = "complex",
    ) -> str:
        kwargs = {
            "model": self._model_for(complexity),
            "max_tokens": 1024,
            "messages": messages,
        }
        if system:
            kwargs["system"] = system
        response = self.llm_client.messages.create(**kwargs)
        return response.content[0].text
```

- [ ] **Step 4: Verificar manualmente — conexao + cache funcionando**

Run (de dentro de `REDIS/llm_router/`):
```
python -c "
from router import LLMRouter
r = LLMRouter()
resp1 = r.ask('Qual e a capital do Japao?')
print('1a resposta:', resp1[:80])
resp2 = r.ask('Qual e a capital do Japao?')
print('2a resposta (deve ser identica, vinda do cache):', resp2[:80])
print('BATE:', resp1 == resp2)
"
```
Expected: imprime `Connected to Redis successfully`, as duas respostas contendo "Tóquio"/"Tokyo", e `BATE: True` (prova que a segunda chamada veio do cache, nao gerou uma resposta nova — a segunda chamada nao precisa necessariamente ser instantanea nem custar zero pra provar isso, mas o texto identico e a evidencia).

- [ ] **Step 5: Commit**

```bash
git add REDIS/llm_router/__init__.py REDIS/llm_router/config.py REDIS/llm_router/router.py
git commit -m "Adiciona llm_router (cache semantico + roteamento de modelo)"
```

---

## Task 2: Integrar o llm_router no agente conversacional

**Files:**
- Modify: `REDIS/agente-conversacional/agent.py` (arquivo inteiro reescrito abaixo — substituir o conteudo atual por este)

**Interfaces:**
- Consumes: `LLMRouter` (Task 1) — `LLMRouter()`, `.redis_client`, `.ask(prompt, system=None, complexity="complex")`, `.ask_with_history(messages, system=None, complexity="complex")`.
- Produces: `ConversationalAgent` mantem exatamente a mesma interface publica de antes — `__init__(self, session_name: str = "chat")` e `chat(self, user_input: str) -> str` — nada muda pra quem chama (`main.py`, Task 4 do plano anterior, ja commitado, nao precisa de nenhuma alteracao).

- [ ] **Step 1: Substituir `REDIS/agente-conversacional/agent.py` inteiro por este conteudo**

```python
"""Agente conversacional: Claude + memoria semantica no Redis.

Chamadas ao LLM passam pelo llm_router (../llm_router) em vez do SDK
Anthropic direto: __init__ usa router.ask() com o mesmo prompt de sempre
("Hello") — candidata perfeita a cache; chat() usa router.ask_with_history()
porque o historico da conversa varia a cada chamada, entao nunca deve ser
cacheado (ver REDIS/llm_router/router.py).
"""
import sys
from pathlib import Path

from redisvl.extensions.message_history import SemanticMessageHistory

# llm_router e um pacote irmao (REDIS/llm_router), nao um subpacote deste
# modulo — este projeto nao usa setup.py/pyproject, entao adicionamos o
# caminho manualmente antes do import.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "llm_router"))
from router import LLMRouter  # noqa: E402

SYSTEM_PROMPT = (
    "You are a helpful assistant that will answer questions based on the "
    "conversation history."
)


class ConversationalAgent:
    def __init__(self, session_name: str = "chat"):
        self.router = LLMRouter()

        try:
            self.router.ask("Hello")
            print("Connected to LLM successfully")
        except Exception as e:
            print(f"LLM connection error: {e}")
            raise

        self.session_manager = SemanticMessageHistory(
            name=session_name,
            redis_client=self.router.redis_client,
        )
        # Looser than redisvl's own default (0.3): we'd rather pull in
        # some borderline-relevant history than miss a useful match, since
        # this is a small prototype where recall matters more than
        # precision. Set once here instead of on every chat() call.
        self.session_manager.set_distance_threshold(0.9)

    def chat(self, user_input: str) -> str:
        # get_relevant() ranks by semantic distance, not chronological
        # order, so its results could otherwise start with role="assistant"
        # (e.g. if a past assistant reply is the closest match). The
        # Anthropic Messages API requires messages[0].role == "user", so an
        # assistant-first context would make the call below raise and fall
        # through to the generic except below (silent loss of memory, no
        # signal that memory was the cause). role="user" restricts context
        # to past user turns only, guaranteeing this can't happen: context
        # is user-only, and we append a fresh user message next.
        context = self.session_manager.get_relevant(
            user_input, top_k=8, role="user"
        )

        messages = list(context)
        messages.append({"role": "user", "content": user_input})

        try:
            assistant_response = self.router.ask_with_history(
                messages, system=SYSTEM_PROMPT
            )
        except Exception as e:
            print(f"Error getting LLM response: {e}")
            return "Sorry, I'm having trouble understanding your question. Please try again later."

        try:
            self.session_manager.add_messages([
                {"role": "user", "content": user_input},
                {"role": "assistant", "content": assistant_response},
            ])
        except Exception as e:
            print(f"Error storing conversation: {e}")

        return assistant_response
```

- [ ] **Step 2: Verificar manualmente — agente continua funcionando igual, agora via router**

Run (de dentro de `REDIS/agente-conversacional/`):
```
python -c "
from agent import ConversationalAgent
a = ConversationalAgent(session_name='smoke_test_router')
r1 = a.chat('Meu prato favorito de carne e picanha na brasa.')
print('R1:', r1[:80])
r3 = a.chat('Qual e o meu prato de carne favorito mesmo?')
print('R3:', r3[:120])
"
```
Expected: imprime `Connected to Redis successfully` e `Connected to LLM successfully`, e a resposta de `R3` menciona "picanha" — prova que a memoria semantica (Task 3 do plano anterior) continua funcionando identica, agora passando pelo `llm_router`.

- [ ] **Step 3: Commit**

```bash
git add REDIS/agente-conversacional/agent.py
git commit -m "Integra o llm_router no agente conversacional"
```

---

## Self-Review (preenchido ao escrever o plano)

**Spec coverage:**
- `ask()` cacheado + `ask_with_history()` so roteado, sem cache → Task 1, Step 3
- Duas instancias de `SemanticCache` por tier → Task 1, Step 3 (`self._caches`)
- `complexity` decidido por quem chama, sem heuristica → Task 1, Step 3 (`_validar_complexity`, sem nenhuma logica de deteccao)
- Config reaproveitando `REDIS/.env` compartilhado → Task 1, Step 2
- Modelos default (`claude-haiku-4-5-20251001` / `claude-sonnet-4-6`) → Task 1, Step 2
- Integracao no agente conversacional (ask() no init, ask_with_history() no chat()) → Task 2
- Interface publica do `ConversationalAgent` inalterada (main.py nao precisa mudar) → Task 2, Step 1 (assinaturas identicas)
- Erros: conexao fatal, chamada pontual propaga/e tratada por quem chama → Task 1 Step 3 (Redis fatal) + Task 2 Step 1 (LLM tratado em `chat()`, igual antes)
- Fora de escopo (heuristica automatica, rastreamento de gasto, TTL, mais de 2 tiers, roteamento entre providers) → nenhuma task toca nisso

**Placeholder scan:** nenhum "TBD"/"TODO" — codigo completo em toda etapa.

**Type consistency:** `LLMRouter.ask(prompt: str, system: str | None = None, complexity: str = "complex") -> str` e `ask_with_history(messages: list[dict], system: str | None = None, complexity: str = "complex") -> str` (Task 1) sao exatamente as assinaturas chamadas em `agent.py` (Task 2). `self.router.redis_client` (Task 1) e o mesmo nome de atributo usado em `agent.py` pra `SemanticMessageHistory`.
