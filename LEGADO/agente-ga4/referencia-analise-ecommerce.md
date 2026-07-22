# Referência — dimensões e métricas relevantes pra análise de tráfego/ecommerce

O catálogo completo do GA4 (`referencia-api.md`) tem **375 dimensões e 95
métricas** — quase tudo é ruído pra esse tipo de análise (CM360/DV360/SA360
são plataformas de mídia que a gente não usa, cohort analysis, app mobile
etc.). Este documento é o recorte curado: só o que responde perguntas reais
de tráfego/ecommerce, puxado do `properties.getMetadata` real da propriedade
Integra Foods (2026-07-22) — os nomes abaixo existem de verdade nessa conta,
não são só o que a documentação genérica do GA4 lista.

**Achado à parte:** a propriedade tem eventos-chave customizados além do
funil padrão de ecommerce — `qualify_lead` e `close_convert_lead`
(aparecem em `sessionKeyEventRate:*` / `userKeyEventRate:*`). Ou seja, tem
tracking de geração de leads configurado ali também, não só compra direta.
Vale confirmar com o usuário se isso é intencional (ex.: B2B/atacado
gerando lead antes da venda) antes de montar qualquer relatório — não
assumir que "conversão" = só `purchase`.

## 1. De onde vem o tráfego (aquisição)

| Campo | Tipo | Uso |
|---|---|---|
| `sessionDefaultChannelGroup` | dim | Canal agrupado pelo próprio GA4 (Paid Search, Organic Search, Direct, Referral...) — melhor ponto de partida pra "de onde vem o tráfego" |
| `sessionSource` / `sessionMedium` / `sessionSourceMedium` | dim | Origem crua (ex: `google / cpc`) — mais granular que o channel group |
| `sessionCampaignName` | dim | Nome da campanha (funciona pra qualquer fonte com UTM, não só Google Ads) |
| `sessionGoogleAdsCampaignName` / `sessionGoogleAdsAdGroupName` / `sessionGoogleAdsKeyword` | dim | Específico do Google Ads — permite cruzar sessão↔campanha sem depender de UTM manual |
| `firstUserDefaultChannelGroup` / `firstUserSource` etc. | dim | Mesma família, mas atribuída ao **primeiro** acesso do usuário (aquisição), não à sessão atual — usar quando a pergunta é "como esse usuário chegou até nós" em vez de "de onde veio esse acesso" |

Ignorar: todas as variantes `Cm360*`, `Dv360*`, `Sa360*` (Campaign
Manager/Display & Video 360/Search Ads 360) — plataformas de mídia
corporativa que a Integra Foods não usa.

## 2. Comportamento / engajamento

| Campo | Tipo | Uso |
|---|---|---|
| `sessions` | met | Volume bruto de sessões |
| `engagedSessions` / `engagementRate` | met | Sessão "engajada" = >10s, ou teve key event, ou 2+ pageviews — melhor proxy de qualidade de tráfego que bounce rate isolado |
| `bounceRate` | met | Inverso de engagement rate — mais familiar pra quem já usa Universal Analytics |
| `averageSessionDuration` | met | Tempo médio de sessão |
| `screenPageViews` / `screenPageViewsPerSession` | met | Volume de pageviews e profundidade de navegação |
| `sessionsPerUser` | met | Recorrência (usuários voltando) |

## 3. Funil de ecommerce (eventos, nível agregado)

Mesma sequência que o `ga4_auditor.py` já audita, mas cada estágio também
tem uma métrica de contagem dedicada na Data API:

| Estágio | Métrica de eventos | Métrica de unidades |
|---|---|---|
| Visualizou item | `itemViewEvents` | `itemsViewed` |
| Adicionou ao carrinho | `addToCarts` | `itemsAddedToCart` |
| Iniciou checkout | `checkouts` | `itemsCheckedOut` |
| Comprou | `ecommercePurchases` / `transactions` | `itemsPurchased` |

`transactions` conta eventos de transação com receita; `ecommercePurchases`
conta especificamente eventos `purchase` — geralmente o mesmo número, mas
não são garantidos como idênticos (`transactions` inclui outros tipos de
evento de compra, como `in_app_purchase`, que não se aplicam aqui mas
existem no schema genérico).

## 4. Receita

| Campo | Uso |
|---|---|
| `purchaseRevenue` | Receita líquida de reembolsos — o número "de verdade" pra ROAS |
| `grossPurchaseRevenue` | Receita bruta, sem descontar reembolso |
| `averagePurchaseRevenue` | Ticket médio por transação — direto do GA4, sem precisar do valor fixo `(AJUSTAR)` que hoje mora no `CLAUDE.<site>.md` do agente-ads |
| `averagePurchaseRevenuePerUser` / `Per Paying User` | Ticket médio por usuário (todos) vs. por comprador (só quem comprou) |
| `refundAmount` / `taxAmount` / `shippingAmount` | Decomposição da transação, se precisar detalhar |

**Achado à parte nº2:** `averagePurchaseRevenue` do GA4 é uma fonte de
ticket médio real, medida — hoje o `CLAUDE.<site>.md` do agente-ads tem
ticket médio como placeholder `(AJUSTAR)` preenchido à mão. Dá pra puxar
isso automaticamente em vez de depender do usuário digitar um número
estimado. Vale considerar quando formos ligar Julio↔GA4↔Ads de verdade.

## 5. Quem compra

| Campo | Uso |
|---|---|
| `totalUsers` / `activeUsers` / `newUsers` | Volume de usuários (todos / ativos no período / novos) |
| `totalPurchasers` / `purchaserRate` | Quantos usuários compraram, e que fração do total isso representa |
| `firstTimePurchasers` / `firstTimePurchaserRate` | Especificamente clientes novos (primeira compra) — separa aquisição de retenção |
| `transactionsPerPurchaser` | Recompra dentro do período |

## 6. Produto (o que vende)

| Campo | Uso |
|---|---|
| `itemName` / `itemId` | Produto específico |
| `itemCategory` (até `itemCategory5`) | Hierarquia de categoria, se o catálogo popular esses parâmetros |
| `itemBrand` / `itemVariant` | Marca / variação (tamanho, sabor, corte — relevante pro segmento de carnes/proteína) |
| `itemListName` / `itemListPosition` | Performance de vitrines/listas (ex: "mais vendidos" x posição no carrossel) |
| `itemRevenue` / `itemsPurchased` | Receita e unidades por item — o relatório "quais produtos vendem mais" |

## 7. Segmentação (cortar qualquer análise acima por)

| Campo | Uso |
|---|---|
| `deviceCategory` | Desktop / Tablet / Mobile |
| `country` / `region` / `city` | Geografia — relevante pra logística de entrega de carnes/perecíveis |
| `landingPage` / `pagePath` | Qual página de entrada ou navegada |

## O que fica de fora de propósito

- **Attribution (83 dimensões)**: modelos de atribuição multi-touch
  (`firstUserGoogleAdsQuery`, etc.) — relevante só quando a análise for
  especificamente sobre modelagem de atribuição, não pra relatório de
  tráfego padrão.
- **Cohort, Publisher, User Lifetime**: caso de uso de app mobile / AdMob —
  não se aplica a um ecommerce web B2C.
- **CM360/DV360/SA360**: como já dito, plataformas de mídia não usadas
  aqui.

## Próximo passo natural

Se/quando o Julio ganhar um tool de GA4, o schema do tool não precisa
expor as 470 opções — só esse recorte (~30 campos) já cobre a esmagadora
maioria das perguntas de tráfego/ecommerce que alguém faria numa conversa.
