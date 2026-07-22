# Planejador + Coder v1 — Design

Data: 2026-07-22
Status: aprovado, pronto pra virar plano de implementação

## Contexto

Terceiro e quarto agentes do `REDIS/CLAUDE.md` (conversacional e
llm_router já entregues). São tratados numa spec só porque são
fortemente acoplados: o coder consome o formato de tarefa que o
planejador produz. O agente de teste/correção fica pra depois (pedido
explícito do usuário).

## Objetivo

- **Planejador**: recebe um pedido em texto, quebra em uma lista ordenada
  de tarefas pequenas (descrição + arquivo alvo), grava no Redis (JSON)
  pro coder consumir.
- **Coder**: agente geral de geração de código — não só pros 3 sites de
  produção, também pra criar/alterar código deste próprio projeto
  (agentes, skills). Diferencial sobre uma chamada de LLM crua: valida a
  sintaxe do código gerado antes de escrever, e tenta de novo uma vez se
  vier inválido — ataca o problema de "erros de sintaxe recorrentes" que
  motivou o pedido.

## Fora de escopo (nesta v1)

- Alterar os 3 sites de produção (`C:\INTEGRAFOODS\www\web2` etc.) — o
  coder escreve só dentro de `HubMktDigital` (guardrail de path,
  verificado em código, não só por instrução). O pipeline dos sites fica
  pra outra spec.
- Agente de teste/correção de erros — próximo, não agora.
- Validação de sintaxe pra linguagens além de Python (o projeto inteiro
  hoje é Python — se o coder gerar algo não-Python, a validação é pulada,
  sem retry).
- Execução/orquestração automática de todas as tarefas de um plano em
  sequência — nesta v1, quem chama o coder decide qual tarefa processar
  (sem loop automático plano→execução completa).

## Arquitetura

Duas bibliotecas Python, mesmo padrão do `llm_router` (sem processo
próprio, quem integra importa e chama), ambas usando `llm_router` pras
chamadas de LLM (nunca o SDK Anthropic direto).

### Planejador (`REDIS/planejador/`)

`Planejador.planejar(pedido: str) -> dict`:
1. Chama `LLMRouter.ask(pedido, system=SYSTEM_PROMPT, complexity="complex")`
   — o prompt de sistema instrui o Claude a responder só com JSON (lista
   de `{"descricao": ..., "arquivo": ...}`).
2. Faz `json.loads` na resposta. Se falhar, tenta mais uma vez incluindo o
   erro de parse no pedido de correção (mesmo padrão de retry do coder,
   ver abaixo). Se falhar de novo, deixa a exceção estourar — quem chama
   decide como tratar.
3. Monta um plano (`{"pedido", "tarefas": [{"id", "descricao", "arquivo",
   "status": "pendente"}, ...]}`) e grava no Redis via `RedisJSON`
   (`redis_client.json().set(f"plan:{uuid}", "$", plano)` — confirmado
   que o módulo `ReJSON` está disponível na instância Redis Cloud do
   projeto). Devolve o plano com o `plano_id` gerado.

Cache: usa `ask()` (cacheado) — mesmo pedido de planejamento, mesma
decomposição, é um reaproveitamento correto (diferente do caso do agente
conversacional, aqui não há histórico de conversa envolvido).

### Coder (`REDIS/coder/`)

`Coder.implementar(tarefa: dict) -> dict` (`tarefa` no formato que o
Planejador produz — `{"descricao", "arquivo", ...}`):
1. Resolve `arquivo` como caminho relativo à raiz do projeto
   (`HubMktDigital/`) e confere que o caminho final não escapa da raiz
   (guardrail contra path traversal, ex. `arquivo: "../../windows/system32/..."`)
   — se escapar, devolve erro sem gerar nem escrever nada.
2. Chama `LLMRouter.ask(descricao, system=SYSTEM_PROMPT, complexity="complex")`
   — o prompt de sistema instrui a responder só com o código completo do
   arquivo, sem markdown/explicação.
3. Valida sintaxe com `ast.parse()` (Python). Se inválido, tenta de novo
   uma vez, incluindo a mensagem de erro no pedido. Se inválido de novo,
   devolve `{"escrito": False, "erro": ...}` sem escrever nada.
4. Se válido, cria os diretórios necessários e escreve o arquivo de
   verdade (`Path.write_text`), devolve `{"escrito": True, "erro": None}`.

Cache: também usa `ask()` — mesma descrição de tarefa, mesmo código
gerado é razoável de reaproveitar (o retry por erro de sintaxe já muda o
texto do pedido, então não conflita com o cache).

## Erros

Mesmo padrão dos outros 2 agentes: falha de conexão (Redis/Anthropic, via
`LLMRouter`) é fatal na inicialização. Falha ao gerar/validar código
específico de uma tarefa não derruba o processo — devolve um dict com
`erro` preenchido, quem chama decide o que fazer (não faz sentido essa
decisão morar dentro do Coder).

## Teste

Sem suite automatizada (mesmo padrão do projeto). Verificação manual: (a)
`Planejador.planejar()` com um pedido real, conferir que o plano gravado
no Redis (`redis_client.json().get(f"plan:{id}")`) tem tarefas com
`descricao`/`arquivo` fazendo sentido; (b) `Coder.implementar()` com uma
tarefa simples de verdade (ex: criar um arquivo Python pequeno dentro do
projeto), conferir que o arquivo foi escrito e que o conteúdo é Python
válido (roda sem `SyntaxError`).
