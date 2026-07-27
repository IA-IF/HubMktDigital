# Gap raw → tool.json — GA4

Auditoria de 2026-07-27 (plano
`docs/superpowers/plans/2026-07-27-cobertura-tool-json.md`, Task 3).
Fonte: `raw/admin_discovery.json` (analyticsadmin v1beta),
`raw/data_discovery.json` (analyticsdata v1beta),
`raw/metadata_3gfoods.json` (376 dimensões + 140 métricas) + o design
`docs/superpowers/specs/2026-07-22-esquema-analise-vendas-design.md`.

## Achado principal: o esquema de vendas (Fases A-D) já está quase todo coberto

Diferente do que o plano supôs antes da auditoria, **as 4 fases do
esquema de análise de vendas já têm tool.json**, não só a Fase A:

| Fase | Plataforma(s) | tool.json | Status |
|---|---|---|---|
| A — Conversão/Vendas (GA4 puro) | GA4 | `TOOLS/GA4/analise_vendas` | Completo |
| B — Eficiência do pago (GA4+Ads) | ADWORDS | `TOOLS/ADWORDS/analise_vendas` (`analise_ads`) | Completo |
| C — Saúde do orgânico (GA4+Search Console) | SEARCH_CONSOLE | `TOOLS/SEARCH_CONSOLE/analise_vendas` (`analise_organico`) | Completo |
| D — Saúde técnica (indexação) | SEARCH_CONSOLE | `TOOLS/SEARCH_CONSOLE/analise_tecnica` | Parcial — Core Web Vitals **desativado de propósito** até ter navegador real conectado (ver descrição do próprio tool.json) |

Ou seja: **`analise_vendas` (GA4) não tem gap dentro do próprio escopo
Fase A** — as 5 etapas do funil, split de canal e taxas de ecommerce já
usam os campos certos de `metadata_3gfoods.json`.

## Gap real: a API `analyticsadmin` inteira está sem nenhuma tool

`data_discovery.json` (`analyticsdata`, usado por `runReport`) está
coberto pelo que `analise_vendas` já consome. Já `admin_discovery.json`
(`analyticsadmin`) — configuração da propriedade GA4 — não tem
**nenhum** tool.json, nem de leitura nem de escrita:

| Recurso admin | Métodos disponíveis | Já coberto? | Prioridade |
|---|---|---|---|
| `conversionEvents` | list/get/create/patch/delete | Não | **Alta** — citado em `elis.md` ("conversões" como parte do que falta) |
| `customDimensions` / `customMetrics` | list/get/create/patch/archive | Não | **Alta** — precisa existir configurado antes de qualquer `runReport` conseguir usar o campo |
| `googleAdsLinks` | list/create/patch/delete | Não | **Alta** — é o elo entre GA4 e a conta Ads (afeta a Fase B) |
| `keyEvents` | list/get/create/patch/delete | Não | Média — parece sobrepor `conversionEvents` na v1beta atual, checar qual é o vigente antes de criar tool duplicada |
| `dataStreams` / `firebaseLinks` / `measurementProtocolSecrets` | list/get/create/patch/delete | Não | Baixa — não citado em nenhum pedido, setup raramente muda |
| `accounts`/`properties` (metadados, `runAccessReport`) | list/get/patch | Não | Baixa — administrativo, não é dado de marketing |

## Recomendação

Primeiro `tool.json` a criar (leitura, sem confirmação): **`auditar_configuracao_ga4`**
— lista `conversionEvents`, `customDimensions`, `customMetrics` e
`googleAdsLinks` configurados na propriedade de um site, pra responder
diretamente ao pedido de `elis.md` ("verificar se estiver completas os
serviços do Google... conversões"). Isso é pré-requisito de leitura
antes de qualquer tool de escrita (`conversionEvents.create` etc.) fazer
sentido — sem saber o que já existe, criar de novo é arriscado
(duplicar evento de conversão já configurado).

Tools de escrita (`conversionEvents.create`, `customDimensions.create`,
`googleAdsLinks.create`) ficam pra Fase 2, com `requer_confirmacao: true`
no mesmo padrão de `criar_campanha` — mudam configuração real da
propriedade GA4 do cliente.
