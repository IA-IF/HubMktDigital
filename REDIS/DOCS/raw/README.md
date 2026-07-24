# Redis/RedisVL — dado bruto coletado (2026-07-22)

Sem curadoria — mesma disciplina do `TOOLS/<GRUPO>/DOCS/`. Introspecção da
lib **instalada de verdade** neste projeto, não memória de treinamento.

Versões exatas: `redisvl==0.23.0`, `redis==7.4.0` (`pip show`).

## Arquivos

- `redisvl_index.json` — 2 símbolos (`SearchIndex`, `AsyncSearchIndex`) —
  criação/gestão de índice vetorial.
- `redisvl_query.json` — 14 símbolos — tipos de query (vector, range,
  filter, aggregation).
- `redisvl_schema.json` — 17 símbolos — definição de schema de índice
  (campos, tipos, algoritmo de vetor).
- `redisvl_extensions_message_history.json` — 4 símbolos — inclui
  `SemanticMessageHistory`, já usada em `REDIS/agente-julio/agent.py`.
- `redisvl_extensions_cache_llm.json` — 5 símbolos — cache semântico de
  resposta de LLM (usado no `llm_router`). **Nota:** o módulo antigo
  `redisvl.extensions.llmcache` está deprecated, o import certo agora é
  `redisvl.extensions.cache.llm` — descoberto ao vivo pelo warning da
  própria lib ao importar o antigo, mesmo padrão do achado
  `conversionEvents`→`keyEvents` do GA4.
- `redisvl_utils_vectorize.json` — 18 símbolos — os "vectorizers"
  disponíveis (que embedding provider usar: OpenAI, HuggingFace, Cohere,
  etc.) — relevante pra decidir com o quê gerar embedding do catálogo
  `TOOLS/`, sem gastar token Anthropic pra isso (embedding não precisa ser
  Claude).
- `redispy_commands_search.json` — 8 símbolos — camada nativa do
  `redis-py` por trás do RedisVL (RediSearch/`FT.*`).
- `redispy_search_fields.json` — os 5 tipos de campo de índice
  (`TagField`, `TextField`, `NumericField`, `VectorField`, `GeoField`) —
  é a peça que decide como cada campo do catálogo `TOOLS/` seria indexado
  (ex: `plataforma` como `TagField`, descrição como campo com
  `VectorField` pro embedding).

## Docs oficiais já existentes (não duplicadas aqui)

`REDIS/DOCS/agent-concepts.md`, `ai-agent-builder.md`,
`memory-and-performance.md` — baixadas antes desta coleta, cobrem conceito
geral de agente + Redis, não a API Python em si.

## Como foi coletado

```python
import inspect
inspect.getmembers(modulo, predicate=inspect.isclass)  # + inspect.signature / inspect.getdoc por classe/metodo
```
Introspecção pura de runtime — não HTTP, não precisa de credencial nenhuma
(é código Python já instalado no ambiente).

## O que NÃO tem aqui

Nenhuma decisão de "usar VectorQuery com HNSW" ou "TagField pra
plataforma" — isso é a etapa de digestão, ainda não feita. Ver
`.claude/skills/learn-redis/SKILL.md` pro motivo.
