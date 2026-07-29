# Entendimento (ponto de partida da nova frente)

> **Status (2026-07-27, fim do dia):** Histórico detalhado desta data
> nos commits do git e nos planos em `docs/superpowers/plans/2026-07-27-*.md`
> (7 planos do núcleo + 1 do POC + 1 do plano-aprovado, todos com
> checklist `[x]` completo) — aqui só o estado atual.
>
> **Núcleo v2** (`ARQUITETURA/nucleo/`): loop de agente canal-agnóstico
> (`agente.py`), validação/reparo de tool input (`validacao_tool.py`),
> memória Redis real com resumo lido de volta (`memoria.py`), execução
> não-bloqueante por chat (`execucao.py`), dispatch genérico de tools
> reais (`executor_tools.py`), Canal Telegram real (`canal_telegram.py`),
> harness sem token (`fake_anthropic.py`), assembly (`main.py`). 53
> testes passando (`pytest ARQUITETURA/ -v`). Nada em `AGENTES/julio/`
> foi tocado. `main.py` nunca teve `rodar()` (long-polling real)
> executado — só testado via chamadas diretas ao loop com Anthropic
> real; rodar contra o Telegram de verdade é decisão ao vivo separada.
>
> **Contrato tool↔agente** (`ARQUITETURA/contrato-tool-agente.md`): a
> regra central descoberta hoje — agente decide/projeta tudo
> (estratégia E sequência de passos), tool só executa fielmente. Tool
> monolítica (uma chamada fazendo várias coisas amarradas) não escala
> pra pedido aberto, mesmo com schema rico — precisa ser decomposta em
> peças pequenas que o agente encadeia.
>
> **Execução genérica de APIs** (`docs/superpowers/specs/2026-07-27-execucao-generica-apis-design.md`,
> POC em `docs/superpowers/plans/2026-07-27-poc-execucao-generica-ads.md`):
> aplicação prática do contrato — em vez de uma tool curada por
> capacidade, cada plataforma ganha `<plataforma>_consultar_schema`
> (schema/discovery real, ao vivo, cacheado no Redis) +
> `<plataforma>_mutate`/`_query` (genérico, o agente decide recurso/
> operação/campos). **Validado com teste REAL, não mock**: pedido de
> segmentação por proximidade (equivalente a "por CEP") — orçamento →
> campanha → critério, 3 chamadas de API real encadeadas numa
> confirmação humana só, sem nenhum código específico escrito pra
> proximidade. Confirmação única funciona via `EstadoConversa.
> plano_aprovado` (persistido no Redis) — tools `requer_confirmacao`
> só pedem confirmação de novo quando o plano anterior já terminou.
>
> Implementado em todas as 4 plataformas:
> - **ADWORDS**: `ads_consultar_schema` + `ads_mutate` (introspecção
>   protobuf do pacote `google-ads` instalado — não tem discovery doc
>   em runtime). `criar_campanha` **retirado** do catálogo ativo,
>   movido pra `ARQUITETURA/referencia/TOOLS_ADWORDS_criar_campanha/`
>   (superado, não deletado).
> - **GA4**: `ga4_consultar_schema` (376 dimensões + 140 métricas reais
>   via `getMetadata`) + `ga4_report` (runReport genérico). Testado com
>   dado real da 3G Foods.
> - **SEARCH_CONSOLE**: `search_console_consultar_schema` +
>   `search_console_query` (dispatch genérico por recurso/método, ex:
>   `searchanalytics.query`, `sitemaps.list`). Testado com dado real.
> - **GTM**: `gtm_consultar_schema` + `gtm_query` (dispatch genérico
>   com caminhos aninhados, ex: `accounts.containers.workspaces.tags`).
>   Testado com dado real (contas Integra Foods/3G Foods reais).
>
> **Limitação de credencial encontrada (precisa de ação do usuário,
> não é código):** GA4 e GTM só têm escopo OAuth `.readonly`
> autorizado hoje — escrita (`ga4_admin_mutate`, criar/editar tags via
> `gtm_mutate`) exigiria escopo `.edit`/`.readonly`→`.edit`,
> re-consentimento OAuth que só o usuário pode fazer (não é algo que
> se resolve no código). Search Console e Ads não têm essa limitação
> (Ads usa SDK próprio sem esse tipo de escopo por método; Search
> Console só tem `.readonly` mesmo, sem operação de escrita relevante
> hoje).
>
> **Bug real achado e corrigido na limpeza pós-POC:** `tool.json` de
> `registrar_pedido_futuro` declarava `modo_entrada: "local"` sem
> nenhum `script` — só funcionava no `AGENTES/julio` antigo por estar
> especial-casado por nome no orchestrator. No dispatch genérico do
> núcleo v2 isso quebraria (`KeyError`). Corrigido: script real,
> persistindo em Redis (lista `pedidos_futuros`) em vez do markdown
> que o antigo usava.
>
> **Catálogo ativo hoje: 15 tools**, todas com `script` válido e
> dispatchável (`ads_consultar_schema`, `ads_mutate`, `analise_ads`,
> `catalogo_produtos`, `analise_vendas` [GA4], `ga4_consultar_schema`,
> `ga4_report`, `registrar_pedido_futuro`, `atualizar_perfil_cliente`,
> `gtm_consultar_schema`, `gtm_query`, `analise_tecnica`,
> `analise_organico`, `search_console_consultar_schema`,
> `search_console_query`). Tools de análise com cálculo real
> (`analise_ads`, `analise_vendas`, `analise_tecnica`,
> `analise_organico`, `catalogo_produtos`) mantidas curadas, per o
> contrato (não são decisão do agente, são fórmula fixa). 91 testes
> passando no total (`pytest ARQUITETURA/ TOOLS/ -q`).
>
> **Site por conversa e perfil de cliente**: portados pro núcleo v2
> (`memoria.py`: `carregar_site`/`salvar_site`/`resetar_site`,
> `carregar_perfil_cliente`, `montar_system_com_perfil`; `main.py`:
> tool `selecionar_site` tratada em `_tools_e_executor`, catálogo
> restrito a `selecionar_site`+`registrar_pedido_futuro` até o site
> ser escolhido). Validado ao vivo (Anthropic real): "Site 3G Foods
> selecionado! ✅", `carregar_site` retornou `"3gfoods"`.
>
> **Correção 2026-07-28**: bug real encontrado no histórico Redis de
> produção — `selecionar_site` chamado no MEIO de uma conversa (pra
> "testar" outro site) não trocava o site das tools daquele mesmo
> turno, porque `criar_executor_tool` fecha o `site` em closure uma vez
> no início da mensagem (`main.py:_tools_e_executor`); `salvar_site`
> só valia a partir da PRÓXIMA mensagem. O agente concluiu (errado) que
> Adoro/Integrafoods não tinham GA4/Search Console/Ads configurados,
> quando na verdade as tools continuaram batendo no site antigo.
> Corrigido restringindo o design: `selecionar_site` só existe no
> catálogo quando `site is None` (início da conversa); trocar de site
> exige `/start`, que reseta histórico (`repositorio.resetar`) e site
> (`resetar_site`) do chat — nunca mais troca no meio do turno.
>
> **Guardrail `validate_only` (dry-run antes de mutação real)**:
> implementado em `ads_mutate/mutate.py` — `executar_mutate` monta um
> `MutateGoogleAdsRequest` com `validate_only=True` e roda primeiro;
> só executa a mutação real se o dry-run não levantar erro. Os outros
> 3 guardrails do spec (`requer_confirmacao=true` incondicional em
> `*_mutate`, `status=PAUSED` hardcoded pra `Campaign`+`create`, escopo
> por site único por execução) já estavam implementados — conferidos
> de novo linha a linha nesta revisão.
>
> **Escrita em GA4/GTM segue bloqueada por escopo OAuth
> `.readonly`** (ver abaixo) — não é gap de código, é decisão do
> usuário (re-consentimento OAuth) ainda não tomada. Os dispatchers
> genéricos (`gtm_query`, `search_console_query`) não têm um filtro
> de método explícito no código, mas isso é seguro hoje porque o
> escopo OAuth authorizado é só leitura — a própria API do Google
> rejeitaria qualquer método de escrita antes de qualquer efeito
> colateral acontecer.
>
> **Sem pendências conhecidas no núcleo v2** neste momento. Próximo
> passo é o deploy no EC2 (ver `infra/ec2/deploy.ps1`) substituindo o
> bot antigo (`AGENTES/julio/main_telegram.py`) pelo novo
> (`ARQUITETURA/nucleo/main.py`).

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

**Atualização (2026-07-27, após auditar `criar_campanha`):** existe uma
causa raiz ainda mais central por trás disso — ver
[`contrato-tool-agente.md`](contrato-tool-agente.md). Usar a API
"direito" não é só sobre completude/otimização técnica; é sobre a tool
NUNCA decidir nada estratégico por conta própria (isso é sempre do
agente) — e esse erro apareceu de novo bem ao vivo, no meu próprio fix
de bidding do `criar_campanha`.

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
