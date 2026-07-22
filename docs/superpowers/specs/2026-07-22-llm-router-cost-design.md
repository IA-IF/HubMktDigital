# Otimizador de custo de LLM v1 (llm_router) — Design

Data: 2026-07-22
Status: aprovado, pronto pra virar plano de implementação

## Contexto

Segundo dos 5 agentes do `REDIS/CLAUDE.md` (o conversacional foi o
primeiro, já entregue e validado ao vivo — ver
`docs/superpowers/specs/2026-07-22-agente-conversacional-redis-design.md`).
Diferente do conversacional, este não é um agente com quem se conversa —
é uma camada transversal que os outros agentes (o conversacional já
existente, e os futuros planejador/coder/teste) usam toda vez que
precisam chamar um LLM.

Do `agent-concepts.md` (`#cost-optimization`): "LLM cost management: Use
appropriate models for different tasks" — a ideia central deste agente.

## Objetivo

Reduzir custo de chamadas a LLM por dois mecanismos, combinados:
1. **Cache semântico** (Redis) — não paga de novo por uma pergunta já
   respondida antes, se uma pergunta semanticamente parecida já foi feita.
2. **Roteamento de modelo** — deixa quem chama escolher entre um modelo
   barato (tarefas simples) e um mais caro (tarefas complexas), em vez de
   sempre usar o mais caro por padrão.

## Por que duas funções, não uma

Cache semântico assume que "a mesma pergunta, em qualquer contexto, tem a
mesma resposta certa" — verdade pra perguntas isoladas ("qual a capital
da França?"), falso pra conversas com memória: o agente conversacional já
construído manda o histórico inteiro a cada chamada, e uma pergunta como
"qual meu prato favorito mesmo?" é semanticamente idêntica entre duas
conversas diferentes, mas a resposta certa depende do que cada uma disse
antes. Cachear nesse caso devolveria a resposta de outra pessoa.

Por isso a biblioteca expõe duas portas de entrada, e quem integra escolhe
a certa pra cada chamada — não há detecção automática de qual usar.

## Arquitetura

Biblioteca Python (`REDIS/llm_router/`), sem processo próprio. Dois
pontos de entrada:

- `ask(prompt, system=None, complexity="complex") -> str` — cacheada
  (Redis `SemanticCache` do redisvl) + roteada por modelo. Uso: perguntas
  isoladas, sem dependência de histórico (ex: chamada de teste de conexão,
  perguntas tipo FAQ).
- `ask_with_history(messages, system=None, complexity="complex") -> str`
  — só roteada, sem cache. Uso: qualquer chamada onde o resultado depende
  do que veio antes (ex: `chat()` do agente conversacional).

`complexity` é `"simple"` (modelo barato) ou `"complex"` (modelo mais
caro, default — mesmo modelo já usado hoje, pra não mudar comportamento
de quem ainda não decidiu usar `"simple"` em lugar nenhum). Quem chama
decide — sem heurística automática de complexidade (isso seria um projeto
à parte, fora de escopo).

## Cache semântico

Duas instâncias de `redisvl.extensions.cache.llm.SemanticCache`, uma por
tier de complexidade (nomes diferentes, ex: `llmcache_simple` /
`llmcache_complex`) — garante que uma resposta gerada pelo modelo barato
nunca seja devolvida quando alguém pede o modelo caro, e vice-versa.
`distance_threshold=0.1` (o default do redisvl) — bem mais rígido que o
`0.9` usado na memória de conversa do agente conversacional, porque aqui
uma pergunta "parecida mas não idêntica" pode ter resposta diferente o
suficiente pra não valer reaproveitar. Sem TTL nesta v1 (mesma decisão já
tomada no agente conversacional — YAGNI, decide depois se crescer demais).

## Config

`REDIS/llm_router/config.py`, carregando o mesmo `REDIS/.env`
compartilhado da raiz do projeto (reaproveita `REDIS_URL` e
`ANTHROPIC_API_KEY` já existentes — mesma conta, mesmo Redis). Duas
variáveis novas:
- `LLM_ROUTER_SIMPLE_MODEL` (default `claude-haiku-4-5-20251001`)
- `LLM_ROUTER_COMPLEX_MODEL` (default `claude-sonnet-4-6`, o mesmo já
  usado hoje no agente conversacional e no LEGADO — manter consistência,
  não é o escopo desta task decidir trocar o modelo default do projeto)

## Integração com o agente conversacional

`REDIS/agente-conversacional/agent.py` passa a usar:
- `ask()` na chamada de teste de conexão do `__init__` (hoje uma chamada
  direta ao SDK com o prompt fixo `"Hello"` — candidata perfeita pra
  cache, é sempre a mesma pergunta).
- `ask_with_history()` dentro de `chat()`, no lugar da chamada direta ao
  SDK Anthropic — mesmo comportamento visível de hoje (mesma resposta
  esperada), só que passando pelo roteador.

`config.anthropic_api_key()`/`config.claude_model()` de
`agente-conversacional/config.py` deixam de ser usados diretamente por
`agent.py` para a chamada ao LLM (continuam existindo, usados só se
precisar no futuro) — quem decide o modelo agora é o `llm_router`.

## Erros

Mesmo padrão do agente conversacional: falha de conexão (Redis ou
Anthropic) na inicialização do router é fatal, com mensagem clara. Falha
pontual numa chamada de `ask()`/`ask_with_history()` propaga a exceção
pra quem chamou — cada agente que integra decide como tratar (o
`agente-conversacional` já tem esse tratamento em `chat()`, só troca a
fonte da exceção).

## Teste

Sem suite automatizada nesta v1 (mesmo padrão do resto do projeto).
Verificação manual: rodar o agente conversacional depois da integração e
confirmar que (a) ele ainda funciona igual (memória semântica intacta,
como já validado), (b) fazer a mesma pergunta isolada duas vezes via
`ask()` mostra a segunda vindo do cache (sem custo de tokens na segunda
chamada — verificável observando que não há uma nova chamada real à API
Anthropic, ex. com um print de debug temporário ou checando as chaves
novas no Redis).

## Fora de escopo (nesta v1)

- Heurística automática de complexidade (quem chama sempre decide)
- Rastreamento/relatório de gasto (tokens, custo em R$/US$) — outro
  agente ou outra v1, não este
- TTL/limpeza do cache
- Suporte a mais de 2 tiers de complexidade
- Roteamento entre providers diferentes (Anthropic vs OpenAI) — só
  troca de modelo dentro da Anthropic nesta v1
