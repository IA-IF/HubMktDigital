# Integrafoods — Tarefas

Lista de tarefas para ajustes na Integrafoods.

## 2026-07-28 — Indexação (Search Console) e redirect de URLs legadas

**Problema:** auditoria via Search Console mostrou 402 URLs descobertas,
0 indexadas.

**Causa raiz:** URLs antigas no formato `product.php` (já indexadas, mas
retornando HTTP 500) coexistindo com as novas URLs `/produto/slug`
(descobertas pelo Google, mas nunca indexadas) — o Google via as duas
versões do mesmo conteúdo, uma quebrada e outra sem sinal de autoridade
acumulado.

**Correção aplicada:**
- Implementados redirects 301 para os 4 padrões de URL `.php` legados,
  apontando pra rota nova correspondente.
- Verificado em dev e no bundle de produção antes do deploy.
- Deploy feito em produção.
- `robots.txt` também ajustado (`Allow: /busca?q=`) pra recuperação de
  SEO.
- Auditoria e plano registrados (Redis + `docs/superpowers/plans/`).

**Status:** deploy concluído; indexação real deve ser confirmada no
Search Console nos próximos dias (Google recrawlar e reprocessar leva
tempo, não é instantâneo).

## 2026-07-28 — Auditoria de SEO on-page

**Objetivo:** levantar problemas reais de SEO nas páginas mais
representativas do site antes de decidir prioridade de correção.

**Páginas alvo (URLs reais, via sitemap):**
- Home: `https://integrafoods.ind.br/`
- Categorias (listagem): `https://integrafoods.ind.br/categorias`
- Categoria (exemplo): `https://integrafoods.ind.br/categoria/101/1`
- Produto 1: `https://integrafoods.ind.br/produto/charque-tras-sertao-80016/134`
- Produto 2: `https://integrafoods.ind.br/produto/acem-g-ribeiro-resfriado-11391/134`
- Produto 3: `https://integrafoods.ind.br/produto/alcatra-comp-grill-boa-carne-resfriado-11680/134`

**Spec — o que checar em cada página:**

1. *On-page básico*
   - `<title>` (texto exato)
   - meta description (texto exato ou "ausente")
   - H1: quantidade e texto; hierarquia H1→H2→H3 faz sentido?
   - `<link rel="canonical">` (aponta pra própria URL? ausente? errado?)
   - Imagens principais/above the fold: `alt` preenchido ou vazio?

2. *Dados estruturados (JSON-LD)*
   - `script[type="application/ld+json"]` presentes: quais `@type`
     (Product, BreadcrumbList, Organization etc)
   - Campos obrigatórios do tipo preenchidos (ex: Product precisa de
     `name`, `image`, `offers`) ou faltando/vazios

3. *Técnico (via browser real, Chrome DevTools)*
   - Console errors/warnings do próprio site (ignorar ruído de
     terceiros como GA)
   - Requisições com erro/404 do próprio domínio
   - Core Web Vitals: LCP em segundos, classificado como bom (<2.5s),
     precisa melhorar (2.5–4s) ou ruim (>4s)

4. *Indexabilidade*
   - Status HTTP real da navegação (esperado: 200)
   - `<meta name="robots">`: existe? diz `noindex`? (grave se aparecer
     em produto/categoria)
   - Atenção a resíduo do bug de indexação anterior: links internos
     ainda apontando pra `.php` em vez da URL nova

**Checklist de execução:**
- [ ] Home — auditar os 4 blocos acima
- [ ] Categorias (listagem) — auditar os 4 blocos acima
- [ ] Categoria (exemplo) — auditar os 4 blocos acima
- [ ] Produto 1 — auditar os 4 blocos acima
- [ ] Produto 2 — auditar os 4 blocos acima
- [ ] Produto 3 — auditar os 4 blocos acima
- [ ] Consolidar achados por severidade/impacto em SEO
- [ ] Registrar resultado final neste arquivo
- [ ] Avisar resumo no grupo telegram_v2

**Status:** execução interrompida a pedido do Eduardo (2026-07-28,
18:10) — retomar mais tarde. Progresso até a interrupção: agente estava
no meio da checagem técnica (console/network/trace) do Produto 3;
páginas anteriores pareciam sem problema grave nos itens já cobertos até
ali, mas isso **não foi verificado/consolidado** — não tratar como
resultado final, só retomar do zero ou do ponto em que parou na próxima
sessão.
