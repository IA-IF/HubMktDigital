# Entendimento (ponto de partida da nova frente)

> **Status (2026-07-27):** Seis planos escritos e executados:
> - Plano 1 — `docs/superpowers/plans/2026-07-27-nucleo-validacao-e-harness.md`:
>   `validacao_tool.py` + `fake_anthropic.py` (contrato de validação +
>   harness sem token).
> - Plano 2 — `docs/superpowers/plans/2026-07-27-nucleo-agente-core.md`:
>   `agente.py` (`processar_turno`/`resolver_pendencia`) — loop
>   canal-agnóstico, pareamento de tool_use paralelo, e retry que
>   preserva contexto na falha transitória (distingue `FalhaPermanente`
>   de `FalhaTransitoria`).
> - Plano 3 — `docs/superpowers/plans/2026-07-27-nucleo-memoria-redis.md`:
>   `memoria.py` (`RepositorioEstado`/`RepositorioEstadoRedis`,
>   `carregar_resumo`/`salvar_resumo`/`montar_system_com_resumo`) —
>   persistência real de `EstadoConversa` e o resumo de conversa
>   **lido de volta** no system prompt (o bug concreto de hoje: era só
>   escrito, nunca consumido).
> - Plano 4 — `docs/superpowers/plans/2026-07-27-nucleo-execucao-nao-bloqueante.md`:
>   `execucao.py` (`DespachanteConcorrente`) — turnos de chats
>   diferentes rodam em paralelo (thread pool), turnos do MESMO chat
>   sempre serializados (lock por chat_id) — resolve o "parece travado"
>   real de hoje (bot single-thread bloqueando todo mundo numa tarefa
>   demorada).
> - Plano 5 — `docs/superpowers/plans/2026-07-27-nucleo-executor-tools.md`:
>   `executor_tools.py` (`criar_executor_tool`) — despacho genérico de
>   qualquer tool real catalogada em `TOOLS/**/tool.json` (mesma
>   mecânica de `AGENTES/julio/agentes.py`, mas falando o vocabulário
>   `FalhaPermanente`/`FalhaTransitoria`), testado com scripts Python
>   reais em `tmp_path` (subprocess de verdade, zero credencial Google).
> - Plano 6 — `docs/superpowers/plans/2026-07-27-nucleo-canal-telegram.md`:
>   `canal_telegram.py` (`CanalTelegram`) — Canal real via Bot API
>   (envio + long poll), preservando a correção de IPv4/retry já
>   validada em produção em `telegram_transport.py` (não era legado —
>   era uma correção de ambiente com causa raiz documentada).
>
> Os seis com checklist 100% marcado `[x]` e código em
> `ARQUITETURA/nucleo/` (49 testes passando, `pytest ARQUITETURA/ -v`).
> Isso cobre os pontos 2, 3, 4, 5, 6 e 7 da lista no fim deste
> documento. Nada em `AGENTES/julio/` foi tocado. O Redis de produção
> (Redis Cloud compartilhado com o bot antigo) foi **zerado** a pedido
> do usuário (2026-07-27) — schema/dados do `AGENTES/julio/` eram
> considerados legado; o bot antigo, se reativado, precisa de
> `/fix_redis` pra reindexar o catálogo de tools antes de voltar a
> funcionar. Falta só: o `main.py` de assembly ligando `CanalTelegram`
> (token real) + `RepositorioEstadoRedis` (Redis real) +
> `criar_executor_tool` (com `discover_tool.catalogar_tools()` real) +
> `DespachanteConcorrente` + `anthropic.Anthropic()` real — isso é
> integração/smoke-test, não unidade pura, e só deve ser ESCRITO E
> RODADO numa sessão em que o usuário confirme testar contra o
> Telegram de verdade. Depois disso, a otimização das TOOLS em si
> contra a doc oficial de cada API (ponto 1 abaixo) é o maior ponto
> ainda em aberto, e o mais independente de todos.

Isso não é um plano fechado — é o meu entendimento atual do objetivo e
dos problemas de fundo, pra servir de ponto de partida da conversa de
redesenho. Vem de quatro fontes: o brief original em `REDIS/CLAUDE.md`
(escrito antes de qualquer linha de código), o histórico de frustração
em `elis.md`, o que eu observei de dentro do código e ao vivo,
debugando o `AGENTES/julio/` numa sessão inteira hoje, e o feedback
direto do usuário sobre a primeira versão deste documento (corrigido
abaixo).

## Qual é o objetivo, de verdade (corrigido)

**O objetivo é simples: criar anúncios no Google Ads que sejam de fato
otimizados e gerem conversão**, pros 3 clientes (Integra Foods, 3G
Foods, Adoro). Não é uma missão dupla de "auditoria técnica completa +
consultoria de marketing" com peso igual — GA4/GTM/Search Console
importam na medida em que alimentam esse objetivo com dado real
(orçamento, público, o que já converte), não como uma frente
independente. Eu superestimei o escopo na primeira versão deste
documento.

O agente precisa **executar** essas campanhas de verdade — credenciais
já existem no projeto — não virar um chatbot que anota pedido pra "o
time" aplicar depois. O gestor não tem um time técnico disponível pra
isso; o agente É o time técnico.

**Correção importante sobre canal:** eu tinha descrito Telegram como
se fosse metade da arquitetura ("conversa síncrona no Telegram" vs.
"fila técnica em background"). Errado — Telegram é só um acesso
facilitado pro agente, sem nenhum peso arquitetural próprio. Não deve
haver diferença nenhuma entre falar com o agente pelo chat do IDE,
pelo Telegram, ou por outro canal qualquer — é o MESMO agente, o canal
é só transporte. A separação que realmente importa (execução em
background vs. decisão em conversa) não tem nada a ver com qual canal
está sendo usado; ela existe dentro do agente, não entre canais.

## O problema real das TOOLS (mais fundo do que eu descrevi)

`TOOLS/ADWORDS`, `GA4`, `GOOGLE_API`, `GTM`, `SEARCH_CONSOLE` são
wrappers finos de API do Google. Eu tinha descrito o problema como "só
falta uma camada de quando usar" — mas o feedback foi mais duro que
isso: a expectativa era que essas tools fossem escritas seguindo a
documentação oficial de cada API, usando os recursos de forma
otimizada (o próprio `REDIS/CLAUDE.md` já falava em "criar um app pra
usar essa API" direito) — e a decepção é que **quase nada disso está
sendo usado de forma otimizada**, mesmo tendo coletado a documentação
oficial bruta (`TOOLS/*/DOCS/raw/`, via skill `learn-api`). Coletamos o
material e não fizemos o trabalho de aplicar de verdade — a curadoria/
aplicação prática nunca aconteceu, só a coleta.

Isso é mais profundo que só faltar um "quando usar": é preciso revisar
se cada tool em si usa a API do jeito certo (campos certos, filtros
certos, os recursos que a doc oficial recomenda pra esse tipo de
análise) antes de sequer pensar na camada de orquestração por cima.

## "Registrar pedido" virou muleta (não é o propósito)

A rotina de anotar demanda ainda não coberta ou erro
(`registrar_pedido_futuro`/`registrar_pedido_projeto`) existia pra
casos excepcionais — o que não tem ferramenta ainda, ou um bug real do
projeto. Na prática virou destino
padrão de qualquer dificuldade, inclusive quando a ferramenta existe e
só falhou uma vez — isso esvazia o propósito original: a anotação devia
ser rara, sinal de gap real, não a saída padrão de qualquer erro.

A causa raiz não é falta de inteligência do modelo — é que **toda
falha de execução hoje é tratada de forma genérica e destrutiva**: erro
na ferramenta → mostra erro cru ou mensagem genérica → descarta o
estado da tarefa em andamento → a próxima mensagem do humano vira uma
conversa do zero, sem contexto nenhum do que estava sendo feito. Sem
saber "isso é uma campanha que falhou por X", o modelo cai na regra
mais genérica do prompt ("se não consegue, registra um pedido"). Falta
uma distinção entre "isso é permanente, não adianta insistir"
(proposta inválida, precisa mudar o pedido) e "isso é transitório"
(dependência faltando, bug já corrigido, hiccup de rede) — e um jeito
barato de simplesmente **tentar de novo a mesma ação** sem re-passar
pelo LLM decidir tudo de novo.

## Fragilidade de execução (o que a sessão de hoje expôs, uma por uma)

Cada bug de hoje foi uma instância *diferente* do mesmo padrão: o
sistema confia demais que "o que o LLM decidiu chamar" já vem no
formato certo, e não tem nenhuma camada de contrato/validação entre a
decisão do modelo e o efeito real:

- `tool_use` paralelo (o modelo chama duas ferramentas no mesmo turno)
  não era tratado — só a primeira ganhava resposta, a segunda ficava
  órfã e quebrava a API na rodada seguinte.
- O schema de input de uma tool é só uma *sugestão* pro modelo, a API
  da Anthropic não garante nem tipo nem campo obrigatório — e nada no
  código verificava isso antes de aceitar o input como válido.
- O ambiente de execução (EC2) não tinha as mesmas dependências Python
  que as tools reais (`google-ads` etc.) precisam — o venv de produção
  e o catálogo de tools nunca tiveram um contrato de dependência
  formal entre si.
- Um modelo de embeddings (usado pra descoberta semântica de tools) era
  recarregado do zero a cada chamada, dentro do mesmo loop de
  tool-calls — em uma instância de ~900MB de RAM isso é o suficiente
  pra travar o processo inteiro por swap.
- Exceção técnica crua (traceback Python) ia direto pro Telegram do
  gestor — que não tem como interpretar isso, e cujo instinto natural
  ("conserta isso") empurra o modelo pro caminho errado (achar que é um
  bug do próprio bot, não uma falha pontual da ação) — reforçando
  diretamente a muleta descrita acima.
- Validação de proposta de campanha checava quantidade mínima de
  título/descrição, mas não os limites reais de caractere do Google
  Ads — só descobria isso na hora H, com a API de verdade rejeitando.

Nenhum desses é "o bug" — são a mesma lacuna estrutural (falta uma
camada de contrato entre decisão do LLM e execução real) aparecendo em
lugares diferentes. Continuar corrigindo instância por instância não
fecha a lacuna.

## Redis: infra criada, mal aproveitada

Criamos conta Redis especificamente pra memória avançada de agente, e
hoje o uso real é raso: perfil de cliente (alguns campos) e um "resumo
de conversa" que é escrito a cada turno e **nunca lido de volta** —
trabalho pela metade, a peça existe e não está ligada a nada. Isso é
só o sintoma mais visível; o ponto maior é que temos material de
referência sobre memória de agente (`REDIS/DOCS/agent-concepts.md`,
`ai-agent-builder.md`) coletado e nunca de fato aplicado — mesmo padrão
do problema das TOOLS: coleta sem aplicação.

## Sobre "dois agentes" e fluxo fixo de perguntas

Confirmado pelo `elis.md`: só faz sentido **um** agente (Julio/o
agente, independente de canal — ver correção acima), não dois
separados — a fusão já foi feita. O problema remanescente não é ter
dois agentes, é o fluxo de perguntas fixo demais (`_sistema()`/schema
por schema) em vez de uma conversa que entende o pedido pelo conteúdo.

## Testar sem gastar token (pedido novo)

Já existe uma peça disso: a skill `protocolo-teste-tools` (H/R/I/P) —
mocka a decisão (Redis/discover_tool e LLM) e roda só a chamada real de
API pra validar UMA tool isolada, sem gastar token Anthropic. O pedido
agora é escalar essa ideia pro sistema INTEIRO: um jeito de testar o
agente e a orquestração completos aqui no IDE — mecânica de estado,
roteamento, tratamento de erro, pareamento de tool_use/tool_result —
com a decisão do LLM mocada/determinística, antes de rodar de verdade
contra a API da Anthropic e gastar token num sistema que ainda pode
estar quebrado. A arquitetura nova precisa nascer com isso como parte
do design, não como reboco depois.

## O que eu acho que a arquitetura nova precisa resolver, na ordem

1. Tools de fato otimizadas pra API oficial de cada serviço — revisão
   antes de qualquer camada de orquestração por cima.
2. Um contrato de validação único entre "o que o LLM decidiu" e "o que
   vai executar de verdade" — pra qualquer tool nova, não reinventado
   por tool.
3. Memória de conversa (Redis) que realmente informa a próxima decisão
   — não escrita que nunca é lida de volta.
4. Falha de execução preserva contexto suficiente pra retomar a MESMA
   tarefa, em vez de resetar a conversa e forçar o modelo a decidir
   tudo de novo do zero — e "registrar pedido" volta a ser exceção,
   não destino padrão de qualquer erro.
5. Agente desacoplado de canal (Telegram/IDE/outro são só transporte).
6. Execução (rodar tool, gerar código, etc.) nunca bloqueia o
   atendimento a outras conversas.
7. Harness de teste local (mock de decisão do LLM) validando a
   mecânica do sistema inteiro antes de gastar token real.

Isso é ponto de partida, não decisão fechada — o próximo passo é
alinhar com você qual desses (ou algum outro que eu não vi) é o mais
urgente pra desenhar primeiro.
