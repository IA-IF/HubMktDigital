# Resumo real do projeto — HubMktDigital

> Materializado em 2026-07-23 a partir da estrutura de arquivos atual (não
> da memória de sessões passadas). Reflete o estado agora — ver `git log`
> pra histórico.

## O que é

Agente de IA pra marketing digital de 3 e-commerces (Integra Foods, 3G
Foods, Adoro), rodando via Telegram. Audita e opera Google Ads, GTM, GA4 e
Search Console das 3 contas. Regra dura: site sempre explícito na conversa,
nunca inferido.

## Duas gerações de código coexistindo

### `LEGADO/` — 1ª geração, congelada, funcional

5 módulos Python independentes, um por API + um orquestrador:

- `agente-ads/`, `agente-ga4/`, `agente-gtm/`, `agente-search-console/` —
  auditores, um por plataforma, cada um com `referencia-api.md` (catálogo
  de métodos da API) e `CLAUDE.<site>.md`.
- `agente-julio/` — orquestrador Telegram original, seleção de site por
  regex livre no texto (`_detectar_site`).
- `skill-onboard-site/` — skill de onboarding de site novo.

Consolidação de `.env` foi feita pela metade (ver `LEGADO/README.md`): os
`.env` novos (`LEGADO/.env` compartilhado + `SITES/<site>/.env`) já
funcionam, mas os `.env.<site>` órfãos dentro de cada `agente-*/` não foram
apagados e os READMEs ainda descrevem o padrão antigo. Não vale terminar
isso a menos que o LEGADO seja reativado — a decisão é substituir, não
remendar (ver [[feedback_nao-remendar-codigo-legado]] na memória).

### `TOOLS/<PLATAFORMA>/` + `REDIS/agente-julio/` — 2ª geração, em construção

Rearquitetura em andamento, desenhada em `entendendno.md` (H/R/I/P) e
`inteligencia.md` (decisões por etapa). Ideia central: cada tool é um
script Python standalone (`sys.executable script.py <site>`, JSON por
stdin/stdout) chamado como subprocess por `agentes.py`, evitando colisão de
módulos irmãos entre tools diferentes.

**Tools portadas e testadas (com testes automatizados):**

| Tool | Caminho | Testes | Função |
|---|---|---|---|
| Catálogo de produtos | `TOOLS/CATALOGO/catalogo_produtos/` | `test_filtro.py`, `test_sitemap.py` | Lê sitemap público, filtra URLs de produto (334 URLs validadas em produção) |
| Análise de vendas GA4 | `TOOLS/GA4/analise_vendas/` | `test_canais.py`, `test_ecommerce_taxas.py`, `test_funil.py` | Funil de conversão, split por canal, taxas de ecommerce |
| Criar campanha Ads | `TOOLS/ADWORDS/criar_campanha/` | `test_validacao.py` | Monta e cria campanha real no Google Ads, sempre **PAUSADA**; corrigido bug de campo EU political advertising (API v24) |
| Análise Ads | `TOOLS/ADWORDS/analise_vendas/` | — | ROAS, CPA, CAC-blended |
| Análise Search Console | `TOOLS/SEARCH_CONSOLE/analise_vendas/` | — | Saúde de indexação e orgânico (achado: 3G Foods em 0% de indexação) |
| Pedido futuro | `TOOLS/GERAL/registrar_pedido_futuro/` | — | Só `tool.json`, sem script — fallback quando nada mais resolve |

`TOOLS/<PLATAFORMA>/DOCS/` guarda referência bruta de API coletada ao vivo
pela skill `learn-api` (não curada — curadoria fica pra quando for indexar
no Redis).

**`REDIS/agente-julio/`** — nome único pra pasta, persona e responsabilidade
de orquestrador (antes espalhado entre "agente-conversacional" no caminho e
"Julio" só na prosa/comentários — normalizado em 2026-07-23). 959 linhas ao
todo:

- `orchestrator.py` (418 linhas) — o Julio conversa no Telegram, site
  nunca assumido por padrão (pergunta antes de tudo, troca com `/site`),
  4 ferramentas explícitas hoje: `consultar_trafego` (leitura),
  `consultar_catalogo_produtos` (leitura), `propor_campanha` (para
  confirmação humana antes de criar de verdade), `registrar_pedido_futuro`.
  Só Anthropic — sem branch OpenAI, client instanciado direto (sem cache
  semântico, porque histórico de conversa muda a cada mensagem).
- `agentes.py` (62 linhas) — ponte pros scripts em `TOOLS/`, via subprocess.
- `discover_tool.py` (122 linhas) — busca vetorial (RedisVL) sobre catálogo
  de `tool.json` indexado no Redis. **Pronto e testado, mas ainda não
  plugado no orchestrator** — as 4 tools continuam hardcoded de propósito
  (mais fácil de auditar); vira relevante quando o catálogo crescer além de
  4 ferramentas. Esse é o design descrito na Etapa 2 de `inteligencia.md`,
  espelhando o próprio `ToolSearch` do Claude Code.
- `julio_config.py`, `pedidos.py`, `telegram_transport.py`,
  `main.py`/`main_telegram.py` — config, fila de pedidos futuros, camada de
  transporte Telegram, entrypoints.

**Etapa 1 do plano** (`/start` com menu fechado de 3 sites, substituindo o
`_detectar_site` por regex) — desenhada em `inteligencia.md`, status de
implementação não confirmado neste levantamento (checar `orchestrator.py`
linha a linha se for ativar).

## Infra de suporte

- `REDIS/` — Redis Cloud como memória de agente. `DOCS/` tem docs oficiais
  baixadas + `DOCS/raw/` com referência bruta coletada por `learn-redis`.
  `llm_router/`, `coder/`, `planejador/` são módulos exploratórios (agentes
  de custo/coder/planejamento cogitados em `REDIS/CLAUDE.md`, não
  confirmado o quanto foram implementados).
- `TOOLS/GOOGLE_API/` — `discover_tool_buscar.py` / `discover_tool_indexar.py`
  (indexação/busca genérica de referência de API), `auth.json`.
- `SITES/<site>/.env` — segredos por site (integrafoods, 3gfoods, adoro) +
  `_template/` pra onboarding de site novo.
- `.claude/skills/` — skills do projeto: `auditoria-ads`, `auditoria-ga4`,
  `auditoria-gtm`, `auditoria-search-console` (leitura, dry-run),
  `learn-api`/`learn-redis` (coleta bruta de referência via introspecção
  ao vivo), `protocolo-teste-tools` (reproduz teste mocado H/R/I/P sem
  gastar token, só pra tools em `TOOLS/`, nunca em `LEGADO/`).

## Docs de contexto na raiz

- `mydata.md` (gitignored) — pedido original, IDs de conta, credenciais de
  referência.
- `pratico.md` — dados práticos das plataformas por site.
- `brainstorm.md` — ideias de arquitetura do agente.
- `entendendno.md` / `inteligencia.md` — design incremental da
  rearquitetura (trace H/R/I/P + decisões por etapa).
- `acesso-guiado.md`, `gtm-workflow.md`, `talk1.md` — não inspecionados
  neste levantamento.

## O que ainda não existe (achados de gap, não tarefas confirmadas)

- Skills de escrita/edição em GTM/GA4/Ads/Search Console (tags, públicos,
  conversões, funil) — hoje só auditoria de leitura.
- Skill de deploy nos 3 sites (Integra Foods e Adoro têm ferramenta própria
  de deploy no repo do site; 3G Foods não, e usa FTP).
  Códigos dos sites ficam fora deste repo:
  `C:\INTEGRAFOODS\www\web2` (Integra Foods),
  `C:\INTEGRAFOODS\www\c3g-web` (3G Foods),
  `C:\INTEGRAFOODS\www\adoro-web` (Adoro).
- Agente de auditoria técnica via browser real + Lighthouse/DevTools.
- Fila de execução separada pra parte técnica vs. parte estratégica
  (marketing/comercial junto com o gestor no Telegram: persona, público,
  segmentação, keywords, escolha de produto/URL antes de propor anúncio).
- `discover_tool.py` plugado de fato no `orchestrator.py`.
