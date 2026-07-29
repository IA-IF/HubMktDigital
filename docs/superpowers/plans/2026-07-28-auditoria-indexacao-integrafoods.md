# Auditoria de Indexação Google — Integra Foods

> Execução: inline, nesta conversa, passo a passo — o usuário revisa e
> aprova cada achado antes do próximo passo. Sem subagentes.

**Goal:** Analisar o estado de indexação do Google para
`integrafoods.ind.br` via Search Console (sitemaps enviados vs.
indexados, erros, avisos) e persistir o resultado no Redis pra virar
série histórica comparável em auditorias futuras.

**Site:** `integrafoods` (explícito, conforme regra do projeto — nunca
inferir).

**Tech Stack:** `TOOLS/SEARCH_CONSOLE/analise_vendas/analise_tecnica.py`
(chamada real à Search Console API, sem custo de token Anthropic) +
`redis-py` (persistência, `REDIS_URL` de `REDIS/.env`).

## Escopo

Só a metade "indexação" da Fase D (sitemaps: submetido/indexado/erros/
avisos). Core Web Vitals fica de fora — depende de navegador real
(chrome-devtools-mcp/Playwright), desativado no código atual de
propósito (`analise_tecnica.py:4-9`).

## Achado conhecido a confirmar

Numa auditoria anterior a Adoro apareceu com 0 sitemaps enviados —
não é o site desta rodada, mas se aparecer algo parecido pro
Integra Foods, não assumir que é bug da tool: é achado real, vira item
de ação.

---

### Passo 1 — Rodar a auditoria técnica real ✅ (2026-07-28)

- [x] Executar `python TOOLS/SEARCH_CONSOLE/analise_vendas/analise_tecnica.py integrafoods`
- [x] Confirmar que retornou `ok`-like (sem exceção) e mostrar o JSON cru pro usuário

Resultado:
```json
{
  "site": "integrafoods",
  "indexacao": {
    "sitemaps": [
      {
        "path": "https://integrafoods.ind.br/sitemap.xml",
        "submetido": 402,
        "indexado": 0,
        "taxa_indexacao": 0.0,
        "erros": 0,
        "avisos": 0,
        "ultimo_download": "2026-07-23T11:18:44.864Z"
      }
    ],
    "total_submetido": 402,
    "total_indexado": 0,
    "taxa_indexacao_geral": 0.0
  }
}
```

### Passo 1.5 — Investigação da causa raiz (0% indexado) ✅ (2026-07-28)

`urlInspection.index.inspect` não dá pra chamar pelo `query.py` genérico
(o método POST exige `body={...}`, não kwargs soltos) — script pontual
descartável em
`.../scratchpad/inspecionar_url.py` só pra essa investigação, não
versionado no projeto.

Achados (via `urlInspection.index.inspect` real, 3 URLs de amostra):

| URL | coverageState | pageFetchState | lastCrawlTime |
|---|---|---|---|
| `/` (home) | **Submitted and indexed** | SUCCESSFUL | 2026-07-28 (hoje) |
| `/produto/picanha-fatiado-gran-carnes-resfriado-12198/134` | Discovered - currently not indexed | UNSPECIFIED (nunca tentou crawlear) | — |
| `/categoria/100/1` | Discovered - currently not indexed | UNSPECIFIED (nunca tentou crawlear) | — |

`robots.txt` não bloqueia `/produto` nem `/categoria` (só `/busca`,
`/login`, `/carrinho`, etc. — todos corretos de bloquear).

**Diagnóstico inicial:** não é bloqueio nem penalidade de qualidade (isso
apareceria como `pageFetchState: SUCCESSFUL` + `verdict: FAIL`). É
"Discovered - currently not indexed" com fetch nunca tentado.

**Causa raiz confirmada (usuário apontou: site foi refeito, pode ter
sobrado algo do antigo):**

`searchanalytics.query` por página (90 dias) mostra que praticamente
todo o tráfego/posições que o Google ainda reconhece pro domínio é do
**site antigo** — padrão de URL `/produto.php?id_prod=...`,
`/quem-somos.php`, `/contato.php`, `/busca.php`, `/segmento.php`. O
sitemap novo usa `/produto/slug-nome-id/categoria`, um padrão totalmente
diferente. Testei se essas URLs antigas ainda respondem:

```
status:500 -> https://integrafoods.ind.br/produto.php?id_prod=106226749
status:500 -> https://integrafoods.ind.br/quem-somos.php
status:500 -> https://integrafoods.ind.br/contato.php
status:500 -> https://integrafoods.ind.br/busca.php?...
status:500 -> https://integrafoods.ind.br/segmento.php?...
```

Todas as URLs antigas devolvem **HTTP 500** (erro de servidor), não
404 nem redirect 301. Ou seja:

1. O Google ainda mostra essas URLs antigas nos resultados de busca
   (impressões e cliques reais nos últimos 90 dias) — usuário clica,
   cai em erro 500. Tráfego real sendo perdido agora.
2. Não existe redirect 301 do padrão antigo (`id_prod=`) pro novo
   (`/produto/slug/id`) — zero autoridade/histórico de ranking
   transferido. Pro Google, as 402 URLs novas são páginas nunca vistas,
   competindo do zero por prioridade de rastreamento.
3. Erros 500 em massa sendo possivelmente rastreados por Googlebot
   também pesam negativamente no orçamento de rastreamento do site
   inteiro.

**Recomendação (ação técnica, fora do escopo desta auditoria de
leitura):** implementar redirects 301 do padrão antigo
(`/produto.php?id_prod=X`, `/quem-somos.php`, etc.) pro padrão novo
correspondente, em vez de deixar 500. Isso resolve os 3 pontos acima de
uma vez.

### Passo 2 — Revisar achados com o usuário

- [x] Interpretar `taxa_indexacao_geral` e a lista por sitemap (`erros`, `avisos`, `ultimo_download`)
- [x] Usuário confirma se algum número é inesperado / já conhecido — confirmado, pediu investigação, causa raiz identificada acima

### Passo 3 — Script de persistência no Redis ✅ (2026-07-28)

- [x] Criar `REDIS/coder/gravar_auditoria.py`, genérico por `tipo` (não só `search_console`, reaproveitável por GTM/GA4/Ads depois):
  - conecta via `redis.from_url(REDIS_URL)` (URL vinda de `dotenv_values(REDIS/.env)`, nunca hardcoded)
  - grava snapshot em `auditoria:<tipo>:<site>:<timestamp ISO>` (JSON string, `SET`)
  - adiciona o timestamp em `auditoria:<tipo>:<site>:historico` (`RPUSH`), pra listar rodadas depois
- [x] Rodar contra o resultado real do Passo 1 + diagnóstico do Passo 1.5 (indexação + causa raiz completos num snapshot só)

Chave gravada: `auditoria:search_console:integrafoods:2026-07-28T19:28:24.579202+00:00`

### Passo 4 — Confirmar gravação ✅ (2026-07-28)

- [x] `LRANGE auditoria:search_console:integrafoods:historico 0 -1` → `['2026-07-28T19:28:24.579202+00:00']`
- [x] `GET auditoria:search_console:integrafoods:<timestamp>` → snapshot completo confirmado de volta

### Passo 5 — Correção técnica: redirects 301 (fora do escopo original de leitura, executado a pedido do usuário) ✅ (2026-07-28)

Código real do site: `C:\INTEGRAFOODS\www\web2\ssr-poc` (Vike + Vue 3, SSR).
Achado do Explore: não existe `server.js`/Express — o "servidor" é o
próprio Vike/Vite, com middlewares plugados em `vite.config.js`
(`configureServer`/`configurePreviewServer`), mesmo padrão já usado por
`createRobotsMiddleware`/`createSitemapMiddleware`. Também não existe
handler de 404 — qualquer rota sem match cai em erro não tratado
(`+onRenderHtml.js`) e vira 500, não só as `.php` antigas.

**Bloqueio real identificado:** `id_prod` (URL antiga) não tem
correspondência confiável com o ID de produto do catálogo novo —
confirmado com o usuário. Decisão dele: sem mapeamento 1:1, usar a
página de busca (`/busca?q=...`) como destino, aproveitando o texto que
a própria URL antiga já carrega (ex:
`?id_prod=123&queijo-parmesao-ralado` → busca por "queijo parmesao
ralado").

- [x] Criado `src/server/legado/middleware.js` (`createLegadoRedirectMiddleware`):
  - estáticas: `/quem-somos.php→/quem-somos`, `/contato.php→/contato`, `/login.php→/login`, `/politica.php→/politica-de-privacidade`
  - `/busca.php?palavra_busca=X → /busca?q=X` (rename de param, mapeamento direto)
  - `/produto.php?id_prod=X&texto-livre → /busca?q=<texto humanizado>`; sem texto livre → `/categorias`
  - `/segmento.php → /categorias` (sem mapeamento confiável de segmento→categoria)
- [x] Plugado em `vite.config.js` (`configureServer` e `configurePreviewServer`, antes dos middlewares de robots/sitemap)
- [x] Testado local com `npm run dev` (porta 3900) — 4/4 redirects 301 corretos
- [x] Testado local com `npm run build && npm run preview` (porta 3901, bundle de produção real) — 4/4 redirects 301 corretos + rota de produto novo (`/produto/slug-id/id_super`) continua 200 normal
- [x] Processos de teste local encerrados, **nada deployado em produção ainda**

- [x] **Deploy pra produção** — rodado via `ssr-poc/DEPLOY/deploy-local.ps1` (confirmado pelo usuário), 2026-07-28. Backup automático em `/var/ssr/integrafoods/producao-backup-20260728-194226`, PM2 recarregado sem downtime, 4/4 redirects confirmados em `https://integrafoods.ind.br` real.

### Passo 6 — Ajuste de robots.txt: liberar indexação de `/busca?q=` ✅ (2026-07-28)

Achado durante revisão: `Disallow: /busca` (já existente, correto pra busca vazia) bloqueava também o destino dos redirects novos (`/busca?q=...`), o que impedia o Google de indexar a página de resultado — ou seja, o redirect resolvia o erro 500 mas não recuperava nenhum sinal de ranking. Usuário escolheu a opção de afinar o robots.txt em vez de manter como estava ou trocar destino pra `/categorias`.

- [x] `src/server/robots/middleware.js`: adicionado `Allow: /busca?q=` depois do `Disallow: /busca` (Google respeita a regra mais específica) — só a busca vazia/genérica continua bloqueada
- [x] Testado local (`npm run build && npm run preview`, porta 3902) — `robots.txt` confirmado com a nova regra, redirect `produto.php` continua 301 normal
- [x] **Deploy pra produção** — segunda rodada, com nova confirmação explícita do usuário (classificador de segurança bloqueou o primeiro comando de deploy repetido sem confirmação nova; usuário reconfirmou). Backup em `/var/ssr/integrafoods/producao-backup-20260728-194654`. `https://integrafoods.ind.br/robots.txt` confirmado em produção com `Allow: /busca?q=`.

**Pendente (não executado, fora do escopo desta sessão):**
- [ ] Adicionar handler de 404 real ao site (achado colateral do Explore — qualquer rota desconhecida, não só `.php` legado, hoje vira 500). Fora do escopo desta correção pontual.
- [ ] Cobrir mais variações de `.php` legado se aparecerem novas no `searchanalytics.query` (ex: `cadastro.php`, `recuperar-senha.php` — não confirmadas com tráfego real ainda, não vale redirect especulativo)
- [ ] Monitorar em auditorias futuras: `taxa_indexacao_geral` do sitemap novo deve começar a subir de 0% nas próximas semanas se os redirects funcionarem como esperado — comparar com o snapshot gravado em `auditoria:search_console:integrafoods:2026-07-28T19:28:24...`

### Próximos passos (fora deste plano, só registrar)

- [ ] `auditoria-search-console` (skill) ainda referencia `LEGADO/agente-search-console/main.py`, que não existe mais (LEGADO foi removido). Vale atualizar a skill pra apontar pra `TOOLS/SEARCH_CONSOLE/analise_vendas/analise_tecnica.py` — não faz parte desta auditoria, avisar o usuário separadamente.
