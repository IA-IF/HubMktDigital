vou tentar explicar como eu te entendi

legenda
H: humano
I: LLM
P: python
R: redis
?: quero que vc coloca quem é o responsavel


vamos criar um cenario mais inteligente, cria na raiz um inteligencia.md e anota um plano curto pra cada etapa que vamos discutir


vamos ter uma comando /start (seja no telegran ou pelo python) 
ele vai trazer isso:
selecione o site
1 3gfoods
2 adoro
3 integrafoods

tem q ser obrigatorio responer uma das opções
a resposta vai fazer a gente usar a pasta correnponder aqui C:\INTEGRAFOODS\teste\HubMktDigital\SITES


pode ser assim


INICIO DE UM NOVO CHAT, 


P: /start
P: carregar IA/GLOBAL.md <nao existe tem que criar> contexto e regras de comportamento e instruções globais pro chat todo
   (e P porque e so leitura de arquivo local — nao precisa de LLM nem de
   Redis pra isso, mesmo padrao do CLAUDE.<site>.md de hoje)
H: 1
P: Vamos trabalhar com a 3gfoods!
P: Carregando as regras de negocio. SITES/3gfoods/RULES.md <usar essas regras como contexto pro chat todo> 
R: Buscando historico, carrega o historico do projeto <depois a gente defini exatamente o que vai entrar ou nao aqui, mas a gente vai salva no redis o que foi feito o que fico pendente etc....>
H: oi
R: discover_tool — busca vetorial pra "oi" nao acha nenhuma ferramenta
   acima do limiar de relevancia -> traz 0 candidatos. `tools=[]` (ou nem
   manda o parametro) nesta chamada ao Claude.
I: sem nenhuma ferramenta disponivel nesta chamada (nao e trafego, nao e
   campanha) -> so
   responde um cumprimento em texto livre. Primeiro token gasto desta
   conversa (P nao tem "if oi" nenhum, quem decide que e so um cumprimento
   e o LLM lendo o GLOBAL.md + RULES.md como contexto)
H: analiza o trafego
R: discover_tool — busca vetorial no catalogo de ferramentas (GA4/GTM/
   Ads/Search Console, dezenas de metodos possiveis, nao so os 3 de hoje)
   e traz so as top-K mais relevantes pra essa mensagem. So ISSO vira o
   `tools=[...]` mandado pro Claude nesta chamada — o catalogo inteiro
   nunca vai de uma vez.
I: entre as top-K que o R trouxe, decide que e sobre trafego -> chama a
   ferramenta consultar_trafego
P: executa a chamada real na API do GA4 e devolve o resultado pro I
   formular a resposta final com os numeros reais


quero cria uma skill de LEARN

ou algo assim, 

quero q vc pesquise a API do GA4 e materializa os rezuldados pra gente saber real quais função o bixo tem, pode ate colocar esse em 

C:\INTEGRAFOODS\teste\HubMktDigital\TOOLS\GA4\DOCS\learn.md





proximas tarefas

prescisa de um TOOL pra ler o catalago de produto de cada site
vamu usar o sitemap , no dir de codigo do site do integrafoods e adoro existe isso, na 3g existe uma verssao muito ruim, a gente tem q atualiza isso tbem e ter essa tool pra saber dos produtos q a gente tem pra vende

E tbem a gente prescisa de uma tool boa, pra faze anuncio no adwords



e por ultima implemenat a orquestração pra usa tudo isso no telegarm , mas tudo , o agente de conversasao, o agente de planejamento, o coisa toda 






ssh -i "C:/Users/rezen/.ssh/IF-AWS.pem" ubuntu@15.229.178.221




/start no telegram: o que acontece? (traço real do codigo hoje)

TODOS os arquivos abaixo (main_telegram.py, orchestrator.py,
telegram_transport.py) moram em AGENTES/julio/ — NENHUM deles ta na
raiz do projeto. So os 2 scripts .ps1 (iniciar-bot/parar-bot) ficam na
raiz, e eles so chamam "python main_telegram.py" de dentro de
AGENTES/julio/.

H: usuario manda "/start" pro bot no Telegram
P [AGENTES/julio/main_telegram.py, funcao rodar_loop]: recebe via long
   polling (chama telegram_transport.receber_atualizacoes) e passa a
   mensagem pra orchestrator.processar_mensagem(chat_id, texto,
   telegram_transport)
P [AGENTES/julio/orchestrator.py, funcao processar_mensagem]: carrega o
   estado do chat (_carregar_estado) — le/cria
   AGENTES/julio/data/telegram_conversas/<chat_id>.json. ARQUIVO LOCAL,
   nao e Redis (Redis so entra depois, no discover_tool)
P [orchestrator.py]: reconhece "/start" -> zera o estado (_estado_vazio)
   e salva de novo (_salvar_estado)

cria ai um arquivo RULES.md
aqui q vamos colocar toa a configuração de IA do agente , personalidade e etc. Todo arquivo tem isso, o julio nao sei o q o julio... . Nao fica tudo aqui. cria no md uma seção pro julio



vamos faze um setup de personalidade, 
resposta curta e objetiva
se nao for evidencia real, fala que TALVEZ, EU ACHO, SUPONHO. NÃO MENTE NEM INVENTA HISTORIA  !!IMPORTANTISSIMO
Trabalha sempre de modo segmentado. Responde uma coisa por vez, faz um passo de cada vez, tarefas curtas




P [orchestrator.py -> telegram_transport.py]: manda a mensagem de
   boas-vindas (telegram_transport.enviar)
P [orchestrator.py -> telegram_transport.py]: manda o menu numerado
   fechado (_perguntar_qual_site):
   selecione o site
   1 3gfoods
   2 adoro
   3 integrafoods
   e retorna

   -> nesse passo todo, NENHUMA chamada a I (Claude) nem a R (Redis)
      acontece. So leitura/escrita de arquivo local, tudo dentro de
      AGENTES/julio/.

H: usuario responde, ex: "2"
P [orchestrator.py, funcao _site_por_opcao]: "2" -> "adoro" (SO aceita
   numero 1/2/3 — texto livre tipo "adoro" ou "quero a adoro" NAO e
   reconhecido, tem que ser o numero)
P [orchestrator.py]: salva o site escolhido no estado, manda "Show,
   vamos tratar da Adoro..." e retorna

   -> ainda sem I nem R aqui tambem.

H: (agora sim, primeira mensagem de verdade) ex: "analiza o trafego"
R [AGENTES/julio/discover_tool.py]: SO AQUI entra o discover_tool —
   busca vetorial no Redis pelas tools candidatas aquela mensagem
I: SO AQUI entra a primeira chamada de verdade ao Claude


msg de verdade, fluxo padrao (testado ao vivo, site=adoro, mensagem
"quero ver o trafego dos ultimos 7 dias" — sem /start antes, direto
com o site ja escolhido):

H: "quero ver o trafego dos ultimos 7 dias"
P [orchestrator.py, processar_mensagem]: nao e /start nem /site, nao
   tem proposta pendente, site ja definido -> pula essas 3 checagens.
   Adiciona a mensagem no historico e chama _perguntar(historico, site)
P [orchestrator.py, _perguntar]: le AGENTES/julio/GLOBAL.md +
   SITES/adoro/RULES.md do disco, monta o system prompt
R [discover_tool.py, descobrir]: busca vetorial no Redis pra essa
   mensagem -> achou a tool `analise_vendas` como candidata (a unica
   relevante pra "trafego")
I [client.messages.create]: 1a chamada ao Claude, com
   tools=[analise_vendas] (so essa, gracas ao discover_tool). O Claude
   decide chamar `analise_vendas` (tool_use, sem input — usa o default
   de 7 dias)
P [orchestrator.py, _executar_tool_leitura -> agentes.py, _rodar]:
   roda TOOLS/GA4/analise_vendas/analise_vendas.py como subprocesso
   (site=adoro), le o stdout como JSON
   >>> BUG achado e corrigido nessa verificacao: agentes.py so lia a
       ULTIMA LINHA do stdout, mas o script imprime JSON bonito
       (multi-linha, indent=2) -> todo tool_result de TODAS as 4 tools
       (GA4, catalogo, criar_campanha) vinha quebrado, e o Claude
       "adivinhava" os numeros certos catando eles de dentro do texto
       de erro. Corrigido: agora le o stdout inteiro. <<<
I [client.messages.create]: 2a chamada ao Claude, agora com o
   tool_result de verdade (JSON limpo: funil de conversao, canais,
   taxas de ecommerce). Sem mais tool_use -> devolve texto final
P [orchestrator.py]: manda esse texto pro usuario via
   telegram_transport.enviar, salva o historico completo (4 turnos:
   user, assistant/tool_use, user/tool_result, assistant/text) no
   arquivo local do chat

   -> nesse fluxo: 1x R (discover_tool), 2x I (Claude), 1x P chamando
      API real do GA4 (subprocesso). Testado ao vivo, dado real da
      conta Adoro (nao mockado).



o norquestrador , coloca um  sistema de funcao fixas

no momento tenho essa, 
fix_redix
reseta no redis os dados que existe do sobre R [discover_tool.py, descobrir]: busca vetorial no Redis, e vai regenera isso
