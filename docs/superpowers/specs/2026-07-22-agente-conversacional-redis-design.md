# Agente Conversacional v1 (Redis + Claude) — Design

Data: 2026-07-22
Status: aprovado, pronto pra virar plano de implementação

## Contexto

`REDIS/CLAUDE.md` pede 5 agentes (custo de LLM, planejador/workflow,
coder, teste/correção, conversação com o humano) coordenados via Redis
Cloud. É grande demais pra uma spec só — este documento cobre **só o
agente conversacional**, o primeiro dos 5, escolhido por ser a porta de
entrada humana.

Referência bruta: `REDIS/generated-reference-conversational-agent.py`,
gerado pelo [AI agent builder oficial da
Redis](https://redis.io/docs/latest/develop/ai/agent-builder/) (opção
Conversational Assistant → Python → Claude), usado como ponto de partida
mas com 3 problemas identificados e corrigidos aqui (ver comentário no
topo do arquivo).

## Objetivo

Um agente conversacional que roda localmente (terminal do VSCode),
conversa em texto com Claude, e lembra o que foi dito antes usando busca
semântica no Redis — não é uma interface de produção (Telegram etc.) por
enquanto, é a base pra validar o padrão de memória via Redis antes de
plugar canal e os outros 4 agentes.

## Arquitetura

Um processo Python CLI. Ciclo por mensagem:

1. Humano digita uma mensagem no terminal
2. Agente busca no Redis (via RedisVL `SemanticMessageHistory`) as
   mensagens do histórico mais *semanticamente relevantes* pra essa
   mensagem (não as últimas N cronológicas — por similaridade vetorial)
3. Monta o prompt: system prompt fixo + contexto relevante + mensagem nova
4. Chama a API da Anthropic (Claude) com esse prompt
5. Mostra a resposta pro humano
6. Grava a troca (pergunta + resposta) de volta no Redis

## Componentes

`REDIS/agente-conversacional/`:

- **`config.py`** — carrega `REDIS/.env` (variáveis: `REDIS_URL` — a
  string `redis://default:...@jocund-macrovivid-button-60700.db.redis.io:19990`
  que já está documentada em `REDIS/CLAUDE.md` — e `ANTHROPIC_API_KEY`).
  Segue o padrão de `_obrigatoria()` já usado nos módulos do LEGADO
  (falha explícita se faltar variável, não silenciosa).
- **`agent.py`** — classe `ConversationalAgent`:
  - Usa o SDK oficial `anthropic` (não o hack `openai.OpenAI(base_url=...)`
    do código gerado, que não funciona de verdade contra a API da
    Anthropic).
  - Usa `SemanticMessageHistory` (RedisVL) para o histórico, com
    `HFTextVectorizer` — modelo de embedding local (`sentence-transformers`,
    baixado uma vez, roda na máquina, sem custo por chamada). Essa escolha
    é deliberada: um dos 5 agentes do projeto é justamente pra *otimizar
    custo de LLM*, então gerar embedding via API paga a cada mensagem iria
    na direção contrária desde o primeiro agente.
  - Mantém o padrão de erro do código gerado: falha de conexão ao Redis é
    fatal (aborta com mensagem clara — sem Redis não há como funcionar);
    falha pontual da chamada ao Claude não derruba a sessão, devolve uma
    mensagem de erro amigável e deixa o loop continuar.
- **`main.py`** — loop de terminal (`while True: input()`), mesmo padrão
  usado nos `main.py` dos módulos do LEGADO. Sem Telegram nem outro canal
  nesta v1 — fica pra quando o design entrar em "qual canal plugar depois".
- **`requirements.txt`** — `anthropic`, `redis`, `redisvl[all]`
  (traz `sentence-transformers` para o `HFTextVectorizer`),
  `python-dotenv`.

## Dados no Redis

Uma `SemanticMessageHistory` por sessão (`session_name`, default `"chat"`).
Cada mensagem vira um vetor indexado, buscável por similaridade. Sem TTL
nem limite de tamanho nesta v1 — se crescer demais, decide-se depois
(fora de escopo agora, YAGNI).

## Teste

Sem suite automatizada nesta v1 (os módulos do LEGADO também não tinham —
consistente com o estágio de protótipo). Verificação manual: rodar o
CLI, trocar 3-4 mensagens, confirmar que uma pergunta de acompanhamento
("o que eu disse sobre X mesmo?") recupera o contexto certo do histórico.

## Fora de escopo (nesta v1)

- Qualquer canal externo (Telegram, WhatsApp, etc.)
- Perfil persistente entre sessões (ex: "site que você estava tratando")
  — decisão deliberada pra não colidir com a regra já validada no projeto
  de nunca inferir/persistir automaticamente qual site está em jogo
- Os outros 4 agentes (planejador, coder, teste, custo de LLM) e qualquer
  coordenação entre eles
- TTL/limpeza de histórico no Redis
