# 3G Foods — Tarefas

Lista de tarefas para ajustes na 3G Foods.

## 2026-07-28 — Texto exibido na busca do Google (title/meta description)

**Problema:** busca `site:loja.3gfoods.com.br` no Google mostra a home
com title "3G Foods" e description "Excelência na distribuição de
alimentos" — texto genérico, sem palavra-chave, sem diferencial.

**Causa raiz encontrada:** `c3g-web/src/router/routes.js` tem DUAS rotas
apontando pro mesmo `HomePage.vue`:
- `path: '/'` (linha 13-17) — a URL real que o Google indexou
  (`https://loja.3gfoods.com.br/`) — **sem** `meta: { title, description }`,
  cai no fallback genérico definido em `router/index.js:31-32`.
- `path: 'home'` (linha 18-22) — tem meta boa (`title: 'Home - 3G Foods'`,
  `description: 'Encontre os melhores alimentos congelados com entrega
  rápida.'`), só que **ninguém acessa `/home`**, todo mundo cai em `/`.

**Decisão de escopo (2026-07-28):** em vez de escrever o texto da home
isoladamente, vamos precisar de vários textos fortes e consistentes
(várias páginas, possivelmente nos 3 sites) — decidido criar um
**skill de copy SEO** (title/meta description dentro do limite de
caractere do Google, com voz/persona por site) em vez de gerar cada
texto ad-hoc. Isso vira pré-requisito antes de aplicar o fix na home.

**Status (2026-07-28):** fix EXECUTADO — `meta` adicionado na rota `/`
(`routes.js`) e H1 acessível adicionado em `HomePage.vue`, usando o
texto já pronto em `TAREFAS/INFOS/Plano_Implementacao_3GFoods_Home.md`
(Melhoria 6) em vez do skill de copy (decisão superada: o texto já
existia pronto, não precisou gerar). Build (`npm run build`) confirmado
sem erro. **Ainda não deployado em produção** — ver
`TAREFAS/plano_acao_3gfoods_home.md` pro plano completo (Fase 1 feita,
Fase 2 com ordem de seções já aprovada, aguardando banners 2/3).

## Referência — CEPs atendidos (segmentação)

`TAREFAS/INFOS/ceps_atendidos_3g.json` — **marcado pelo Eduardo como
informação incorreta (2026-07-28)**. Não usar pra validar números,
segmentação de Ads ou qualquer decisão até ser corrigido/confirmado de
novo.
