# HubMktDigital

Agente de IA para marketing digital de 3 e-commerces de proteína/alimentos
(**Integra Foods**, **3G Foods**, **Adoro**). Orquestra Google Ads + GTM +
GA4 + Search Console via Telegram: audita contas existentes, responde
perguntas sobre tráfego/vendas e propõe/aplica mudanças de campanha.

## Como funciona (visão rápida)

Bot Telegram (`Julio`) com seleção obrigatória de site por conversa:

```
H: /start
P: selecione o site
   1 3gfoods
   2 adoro
   3 integrafoods
H: 2
P: Show, vamos tratar da Adoro...
H: quero ver o trafego dos ultimos 7 dias
R: discover_tool -- busca vetorial no Redis acha a tool certa (ex: analise_vendas)
I: Claude decide chamar a tool com so as candidatas relevantes (nunca o catalogo inteiro)
P: roda o script real da API (GA4/Ads/GTM/Search Console) como subprocesso
I: Claude formula a resposta final com os dados reais
P: manda a resposta pro usuario no Telegram
```

Legenda usada nos docs do projeto: **H** = humano, **I** = LLM (Claude),
**P** = Python, **R** = Redis (busca vetorial de ferramentas).

Ver `entendendno.md` (traço passo a passo do fluxo real de código) e
`inteligencia.md` (decisões de design por etapa) para o detalhe completo.

## Estrutura

```
AGENTES/julio/     orquestrador do bot Telegram (main_telegram.py, orchestrator.py,
                    discover_tool.py = busca vetorial de ferramentas no Redis)
TOOLS/              scripts reais por plataforma (GA4, ADWORDS, GTM, SEARCH_CONSOLE,
                    CATALOGO, GERAL) -- cada um roda como subprocesso, chamado pelo
                    orquestrador conforme o discover_tool indica
SITES/              config e regras de negocio por site (3gfoods, adoro, integrafoods)
                    -- cada pasta tem seu .env e RULES.md
REDIS/              infra de memoria de agente (Redis Cloud): busca vetorial do
                    catalogo de tools, historico de conversa, llm_router, planejador
infra/ec2/          deploy.ps1 (deploy pra instancia EC2 onde o bot roda em producao)
entendendno.md      traço H/I/P/R do fluxo real de codigo, discutido passo a passo
inteligencia.md     decisoes de design por etapa (o "porque", nao o "como")
pratico.md          dados praticos das plataformas por site
brainstorm.md       ideias de arquitetura do agente
```

## Regras do projeto (ver CLAUDE.md para o detalhe)

- **Site sempre explícito na conversa** — nunca auto-descoberta/inferência
  de qual site está em jogo (sempre passa pelo menu `/start`).
- **Segredos só em `.env` gitignored** — nunca em CLAUDE.md, docs ou
  commits (histórico bruto/credenciais de referência ficam em `mydata.md`,
  gitignored, não versionado).
- **Plugins instalados devem ser usados sempre que forem relevantes** —
  lista e status em `REDIS/plugins.md`.

## Rodar localmente

```powershell
.\iniciar-bot.ps1   # sobe o bot em background (logs em AGENTES/julio/data/julio.log)
.\parar-bot.ps1     # derruba o bot
```

Precisa dos `.env` na raiz, em `REDIS/`, e em cada `SITES/<site>/` (ver
`SITES/_template/.env.example` pro formato) — nenhum deles é versionado.

## Deploy (produção — EC2)

```powershell
.\infra\ec2\deploy.ps1
```

Faz `git push` local, `git pull` na instância via deploy key SSH
somente-leitura, reinstala dependências e reinicia o bot em background.
Detalhes de acesso em `infra/ec2/README.md`.

## Status atual

Arquitetura em rearquitetura incremental, do zero, design discutido em
`entendendno.md`/`inteligencia.md`: Etapa 1 (`/start` + seleção de site) e
Etapa 2 (`discover_tool` via busca vetorial no Redis) implementadas — ver
`inteligencia.md` para o histórico completo de decisões e o que ainda
falta (comandos fixos `/fix_help`, `/fix_redis`, `/fix_julio`, tool de
catálogo de produtos via sitemap, tool de criação de anúncios Ads).
