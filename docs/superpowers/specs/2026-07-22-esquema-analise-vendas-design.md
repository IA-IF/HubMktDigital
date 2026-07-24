# Esquema de análise de vendas/conversão multiplataforma — design

## Contexto e motivação

O GA4 já tem relatórios prontos por "Objetivo de negócio" (Gerar leads,
Aumentar as vendas, Entender o tráfego, Ver engajamento/retenção) — cada
um agrupando alguns relatórios pré-fabricados (ex: em "Aumentar as
vendas": Visão geral, Compras de e-commerce, Promoções, Jornada de
compra, Jornada de finalização da compra, Transações).

Decisão explícita do usuário: **não duplicar esses relatórios do GA4**
como ferramentas 1:1. O objetivo real é vender/converter, e isso depende
de tráfego pago **e** orgânico — então o esquema de análise certo **cruza
as 4 plataformas** (GA4, Ads, GTM, Search Console) em vez de replicar a UI
de uma só. Cada relatório do GA4 vira, no máximo, uma peça de dado bruto
que alimenta a análise, não o produto final.

Natureza do documento: **plano vivo**, revisitado/enriquecido no futuro
com outras pegadas de análise — não é uma versão final fechada.

## Pesquisa que embasa o desenho

### KPIs de marketing/conversão (pago vs. orgânico)

- Conversão geral: 2-3% é a média de ecommerce, 5%+ é excelente; varia
  muito por canal — email 4-5%+, orgânico ~3.5%, pago social ~0.5-1.5%.
- ROAS saudável no Google Ads: 3-4x, excelente 6x+.
- CPA saudável: 20-30% do ticket médio (AOV).
- CTR de busca paga: referência ~5%+; Impression Share em termos de
  marca ≥80% evita concorrente "roubando" cliente que já te procura.
- Add-to-cart rate ≥12% indica bom fit de produto/merchandising.
- Checkout completion rate ≥70% indica fricção baixa no checkout.
- **CAC "blended"** (gasto total de marketing ÷ clientes novos totais) é
  30-50% maior que o CAC que o Ads reporta sozinho — a diferença é o
  valor que o canal orgânico contribui de graça e o CAC por-plataforma
  esconde.
- LTV:CAC ≥ 3:1 é o "north star" de unit economics saudável.
- Split de busca de marca vs. não-marca: não-marca <30% do total é
  saudável (mostra que o crescimento não depende só de quem já conhece a
  marca).
- Sinal acionável mais direto da pesquisa: se o canal pago converte pior
  que o orgânico (padrão comum), a alavanca mais rápida de resultado não
  é otimizar anúncio — é realocar budget pra SEO/conteúdo.

Fontes: [Digital Marketing KPIs 2026: 100+ Metrics Reference](https://www.digitalapplied.com/blog/digital-marketing-kpis-2026-100-metrics-reference),
[2026 Ecommerce Conversion Rate Benchmarks](https://buildgrowscale.com/ecommerce-conversion-rate-benchmarks),
[Understanding KPIs in eCommerce: CR, ROAS, LTV](https://www.promodo.com/blog/kpis-in-ecommerce).

### Definição oficial dos relatórios de funil do GA4 (usados como fonte de dado, não como produto)

- **Jornada de compra**: funil de 5 etapas — `session_start` →
  `view_item` → `add_to_cart` → `begin_checkout` → `purchase`. Fechado
  por padrão (usuário que pula uma etapa cai do funil), com toggle pra
  aberto. Métricas: taxa de abandono e retenção por etapa. Segmentável
  por browser/cidade/país/dispositivo/idioma/região.
- **Jornada de finalização de compra (checkout)**: funil fechado de 4
  etapas dentro do checkout — `begin_checkout` → `add_shipping_info` →
  `add_payment_info` → `purchase`.
- **Compras de e-commerce**: detalhe por produto (marca/nome/ID/categoria
  até 5 níveis) x receita, itens comprados/visualizados/no carrinho.
- **Promoções**: `view_promotion`/`select_promotion` → CTR de promoção
  interna, `itemPromotionName`, `itemPromotionClickThroughRate`.
- Nenhum desses tem endpoint de API dedicado — todos são montados via
  `runReport` com a combinação certa de dimensão/métrica (já catalogadas
  em `TOOLS/GA4/DOCS/raw/metadata_3gfoods.json`).

Fontes: [Ecommerce purchases report](https://support.google.com/analytics/answer/12924131?hl=en),
[Purchase journey report](https://support.google.com/analytics/answer/13128171?hl=en-EN),
[Checkout journey report](https://support.google.com/analytics/answer/14000977?hl=en),
[Promotions report](https://support.google.com/analytics/answer/13458990?hl=en).

### Saúde técnica do site (framework 2026)

5 fases em ordem de prioridade: **crawlability/indexação** → arquitetura/
link interno → **Core Web Vitals** → dados estruturados → conteúdo
duplicado. Dado forte: páginas no quartil superior de LCP (<2.5s) têm
**24% mais CTR orgânico** que páginas fora do padrão — performance técnica
afeta o número de negócio diretamente, não é só boa prática.

Fontes: [Technical SEO Audit Checklist Guide 2026](https://www.digitalapplied.com/blog/technical-seo-audit-checklist-guide-2026),
[The Technical SEO Audit: A Practical Framework (2026)](https://www.ewrdigital.com/blog/technical-seo-audit).

## O esquema — 4 fases progressivas

Cada fase é incremental (não precisa da seguinte pra ter valor sozinha) e
cruza mais fontes conforme avança.

### Fase A — Conversão/Vendas (só GA4)

- Funil completo (`session_start`→`purchase`) com abandono por etapa
- Split de sessão por canal (pago/orgânico/direto) + taxa de conversão de
  cada canal separadamente
- Add-to-cart rate, checkout completion rate, AOV

Fonte de dado: só GA4 (`TOOLS/GA4/DOCS/raw/metadata_3gfoods.json` já tem
os campos — `sessionDefaultChannelGroup`, métricas de ecommerce, etc.)

### Fase B — Eficiência do pago (GA4 + Ads)

- ROAS, CPA, CTR, Impression Share (Ads)
- CAC "blended" (gasto Ads ÷ clientes novos do GA4) **vs.** CAC
  só-Ads reportado pela própria plataforma — a diferença entre os dois
  quantifica o que o orgânico contribui

Fonte de dado: Ads (`TOOLS/ADWORDS/DOCS/raw/google_ads_fields.json`) + GA4.

### Fase C — Saúde do orgânico (Search Console)

- Sessões orgânicas (GA4) e sua tendência
- Split busca de marca vs. não-marca (`searchanalytics.query` com
  dimensão `query`, precisa de lista de termos de marca por site)
- CTR de busca e posição média

Fonte de dado: Search Console (`searchanalytics.query`, já catalogado em
`TOOLS/SEARCH_CONSOLE/DOCS/raw/discovery.json`) + GA4.

### Fase D — Saúde técnica (Search Console + GTM + browser real)

- Crawlability/indexação: `urlInspection.index.inspect`, `sitemaps.list`
  (Search Console)
- Core Web Vitals: via Lighthouse real (plugin `chrome-devtools-mcp`,
  já instalado nesta sessão) — **não** é uma API do Google, é o
  navegador rodando de verdade contra o site
- Saúde de tags: `TOOLS/GTM` (triggers órfãos, tags sem trigger — já
  coberto pela auditoria dinâmica existente em `LEGADO/agente-gtm`)

## Explicitamente fora de escopo agora

- **Qual LLM narra/interpreta os números pro humano** (Anthropic vs.
  OpenAI via `llm_router` adaptado) — discutido, mas adiado pra quando a
  Fase A tiver dado real rodando; ver `entendendno.md`/`inteligencia.md`.
- **Estrutura de pastas/ferramentas exata** (`TOOLS/GA4/AUMENTAR_VENDAS/`
  com subpastas foi cogitado, mas a decisão de duplicar por fase A-D ou
  manter uma estrutura só por plataforma fica pra quando a Fase A for
  implementada de verdade — este documento é sobre o quê analisar, não
  ainda sobre como organizar o código).
- Indexação/digestão via Redis do catálogo `TOOLS/*/DOCS/raw` (Etapa 2 de
  `inteligencia.md`) — independente deste esquema, trilha separada.
- Cálculo de LTV real (precisa de dado de recorrência de cliente que
  ainda não confirmamos existir nos 3 sites).

## Próximo passo

Implementar a Fase A primeiro (só GA4, sem dependência de outra
plataforma) — quando isso estiver pronto e testado ao vivo, decidir com o
usuário se a Fase B entra na mesma sessão ou depois.
