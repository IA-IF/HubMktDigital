# Cobertura raw → tool.json (Fase 1: Auditoria) Implementation Plan

> **STATUS: PRONTO — todas as decisões fechadas em 2026-07-27, tasks
> ordenadas por prioridade (GTM → ADWORDS → GA4 → SEARCH_CONSOLE).**

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mapear, pra cada uma das 4 plataformas (GTM, ADWORDS, GA4,
SEARCH_CONSOLE), quais capacidades já documentadas em `TOOLS/<PLATAFORMA>/DOCS/raw/`
(o "como", coletado pelas skills `learn-api`) ainda não têm um `tool.json`
equivalente (o "o quê", orientado a objetivo) — e produzir um relatório de
gap por plataforma que vai virar a Fase 2 (criação dos tool.json faltantes).

**Contexto (ver conversa em `elis.md`):** o discover_tool já indexa só
`tool.json` (goal-oriented) e explicitamente exclui `DOCS/raw` (ver
`TOOLS/GOOGLE_API/discover_tool_indexar.py:46-52`) — a separação "como" vs
"o quê" está correta na arquitetura. O problema real é cobertura: hoje só
existem 7 `tool.json` no projeto inteiro (GA4 ×1, ADWORDS ×2,
SEARCH_CONSOLE ×2, CATALOGO ×1, GERAL ×1) e **GTM tem zero** — só
`TOOLS/GTM/DOCS/raw/discovery.json`, nenhum diretório de tool. Se o
usuário pedir algo que dependa de GTM, o discover_tool não acha nada.

**Architecture:** Cada task de auditoria lê o(s) arquivo(s) raw de uma
plataforma, lista os `tool.json` que já existem pra ela, e escreve um
relatório markdown em `TOOLS/<PLATAFORMA>/DOCS/gap_tool_json.md` com:
capacidades do raw, se já tem tool.json cobrindo (mesmo que parcialmente),
e uma recomendação (criar tool.json novo / já coberto / não vale a pena
expor como tool). Não cria nenhum `tool.json` novo nesta fase — só
levanta o gap.

**Tech Stack:** Leitura de JSON (`TOOLS/*/DOCS/raw/*.json`) + os 7
`tool.json` existentes. Sem código Python novo nesta fase — as tasks são
de leitura/análise, saída em markdown.

## Global Constraints

- Nenhuma task desta fase cria ou modifica `tool.json` — só relatórios de
  gap. Criar os tool.json novos é Fase 2, fora deste plano (depende do
  resultado da auditoria — ver "Em aberto").
- Não ler nem importar nada de `LEGADO/`.
- Relatório de gap por plataforma vai em `TOOLS/<PLATAFORMA>/DOCS/gap_tool_json.md`
  (ao lado do `README.md` que já existe em cada `DOCS/`).
- Cada capacidade listada no relatório precisa apontar o campo/método real
  do raw (ex.: `apiName` do GA4, `resource_name` do Ads, nome do recurso do
  GTM) — não inventar nome, conferir contra o raw.

---

### Task 1: Auditoria GTM (o caso mais claro — zero tool.json hoje)

**Files:**
- Read: `TOOLS/GTM/DOCS/raw/discovery.json`
- Read: `TOOLS/GTM/DOCS/README.md`
- Create: `TOOLS/GTM/DOCS/gap_tool_json.md`

**Interfaces:**
- Produces: `TOOLS/GTM/DOCS/gap_tool_json.md` com uma tabela: capacidade
  (nome do recurso/método GTM) | descrição goal-oriented proposta | tem
  tool.json? (não, sempre, nesta task) | prioridade (alta/média/baixa,
  critério: usado nos fluxos de auditoria do container hoje, ver skill
  `auditoria-gtm`, ou não).

- [ ] **Step 1: Ler o discovery.json e listar todos os recursos/métodos do container GTM (tags, triggers, variables, versions, workspaces)**
- [ ] **Step 2: Cruzar com o que a skill `auditoria-gtm` já lê hoje via API (ver `.claude/skills/auditoria-gtm/`) — o que já é lido mas não é uma tool invocável pelo Julio**
- [ ] **Step 3: Escrever `TOOLS/GTM/DOCS/gap_tool_json.md` com a tabela de gap e uma recomendação do primeiro tool.json a criar (ex.: `listar_tags_triggers`, goal-oriented, não "chamar GTM API tags.list")**
- [ ] **Step 4: Commit**

```bash
git add TOOLS/GTM/DOCS/gap_tool_json.md
git commit -m "docs: mapeia gap raw->tool.json do GTM"
```

### Task 2: Auditoria ADWORDS (já tem 2 tool.json — achar o que falta)

**Files:**
- Read: `TOOLS/ADWORDS/DOCS/raw/google_ads_fields.json`, `TOOLS/ADWORDS/DOCS/raw/services.json`
- Read: `TOOLS/ADWORDS/analise_vendas/tool.json`, `TOOLS/ADWORDS/criar_campanha/tool.json`
- Create: `TOOLS/ADWORDS/DOCS/gap_tool_json.md`

**Interfaces:**
- Produces: mesmo formato de tabela da Task 1, mas já descontando as
  capacidades cobertas por `analise_vendas` (eficiência de campanha) e
  `criar_campanha` (criação/validação de campanha).

- [ ] **Step 1: Listar os `services.json`/`google_ads_fields.json` relevantes pra e-commerce (campanhas, grupos de anúncio, keywords, lances, negative keywords — ver `analise_video.md`/`video.md` sobre SKAG se existirem no repo)**
- [ ] **Step 2: Marcar o que `analise_vendas` e `criar_campanha` já cobrem, ler os dois `tool.json` pra confirmar escopo real (não assumir pelo nome)**
- [ ] **Step 3: Escrever `TOOLS/ADWORDS/DOCS/gap_tool_json.md` com o que falta (ex.: negative keywords, ajuste de lance, pausar/ativar campanha — só incluir se houver evidência no raw de que a API suporta)**
- [ ] **Step 4: Commit**

```bash
git add TOOLS/ADWORDS/DOCS/gap_tool_json.md
git commit -m "docs: mapeia gap raw->tool.json do ADWORDS"
```

### Task 3: Auditoria GA4 (já tem 1 tool.json — achar o que falta)

**Files:**
- Read: `TOOLS/GA4/DOCS/raw/admin_discovery.json`, `TOOLS/GA4/DOCS/raw/data_discovery.json`, `TOOLS/GA4/DOCS/raw/metadata_3gfoods.json`
- Read: `TOOLS/GA4/analise_vendas/tool.json`
- Create: `TOOLS/GA4/DOCS/gap_tool_json.md`

**Interfaces:**
- Produces: mesmo formato de tabela, descontando o que `analise_vendas`
  já cobre (funil, canais, taxas de ecommerce — ver
  `docs/superpowers/plans/2026-07-22-esquema-analise-vendas-fase-a.md`
  pra escopo exato da Fase A).

- [ ] **Step 1: Listar relatórios/dimensões/métricas do `data_discovery.json` + `metadata_3gfoods.json` fora do que a Fase A do `analise_vendas` já usa**
- [ ] **Step 2: Checar o `admin_discovery.json` por capacidades de admin (custom dimensions, conversion events, links de Ads) que hoje só existem como raw**
- [ ] **Step 3: Escrever `TOOLS/GA4/DOCS/gap_tool_json.md` com o gap (ex.: Fases B/C/D do esquema de análise de vendas, se ainda não implementadas — conferir)**
- [ ] **Step 4: Commit**

```bash
git add TOOLS/GA4/DOCS/gap_tool_json.md
git commit -m "docs: mapeia gap raw->tool.json do GA4"
```

### Task 4: Auditoria SEARCH_CONSOLE (já tem 2 tool.json — achar o que falta)

**Files:**
- Read: `TOOLS/SEARCH_CONSOLE/DOCS/raw/discovery.json`
- Read: `TOOLS/SEARCH_CONSOLE/analise_vendas/tool.json`, `TOOLS/SEARCH_CONSOLE/analise_tecnica/tool.json`
- Create: `TOOLS/SEARCH_CONSOLE/DOCS/gap_tool_json.md`

**Interfaces:**
- Produces: mesmo formato de tabela, descontando `analise_vendas`
  (orgânico) e `analise_tecnica` (técnico/indexação).

- [ ] **Step 1: Listar métodos do `discovery.json` (sitemaps, searchAnalytics, URL inspection) fora do que os 2 tool.json já cobrem**
- [ ] **Step 2: Cruzar com a skill `auditoria-search-console` (que hoje é só leitura de sitemap/indexação) pra ver se há capacidade de escrita (submeter sitemap, pedir inspeção) documentada no raw mas não exposta como tool**
- [ ] **Step 3: Escrever `TOOLS/SEARCH_CONSOLE/DOCS/gap_tool_json.md`**
- [ ] **Step 4: Commit**

```bash
git add TOOLS/SEARCH_CONSOLE/DOCS/gap_tool_json.md
git commit -m "docs: mapeia gap raw->tool.json do SEARCH_CONSOLE"
```

---

## Decisões (2026-07-27 — decidido por mim a pedido do usuário: "menor atrito, mais simples, mais compatível com o projeto")

- **Fase 2 fica mesmo separada.** Este plano só produz os relatórios de
  gap; criar os `tool.json` novos vira plano à parte depois que as Tasks
  1-4 rodarem — não dá pra especificar tasks concretas de algo que ainda
  não foi levantado.
- **Prioridade entre plataformas: GTM primeiro** (zero cobertura hoje,
  o gap mais óbvio), **depois ADWORDS** (alimenta direto o plano de
  pesquisa de técnica/campanha, que já tem trabalho ativo — SKAG spec),
  **depois GA4** (só falta o que passa da Fase A do esquema de vendas),
  **SEARCH_CONSOLE por último** (já é só leitura, menor urgência).
- **Tools de escrita novas reusam o mesmo padrão de confirmação**
  (`propor_campanha`), não um fluxo de aprovação próprio por tool —
  mesma decisão já tomada no plano de pesquisa de técnica
  (`2026-07-27-pesquisa-tecnica-perfil-cliente.md`), por consistência:
  um padrão de confirmação só, reusado, é mais simples que um por tool.
- **Curadoria raw→tool.json continua manual por enquanto.** Não vale
  construir uma skill/etapa automatizada antes de ver o volume real de
  gap que a auditoria (Tasks 1-4) vai revelar — automatizar cedo demais
  é atrito extra sem necessidade comprovada ainda.
