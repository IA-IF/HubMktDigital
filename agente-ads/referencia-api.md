# Referência — o que a API do Google Ads oferece (e o que a gente usa hoje)

Mesmo espírito dos outros 3 (`agente-ga4`, `agente-gtm`,
`agente-search-console`), mas a API em si é bem diferente: não é um
discovery document REST, é gRPC/protobuf via a lib `google-ads`. O
equivalente ao `getMetadata` do GA4 aqui é o `GoogleAdsFieldService`, que
listei ao vivo em 2026-07-22 (`SELECT name, category ... WHERE category =
'RESOURCE'`, sem `FROM` — sintaxe própria desse service).

**183 recursos consultáveis por GAQL.** É de longe a maior das 4 APIs do
projeto — a maioria é de features que não usamos (hotel, travel, local
services, Performance Max, audiências avançadas). Este documento já vem
pré-filtrado pro que é relevante pro nosso caso (ecommerce de
carnes/proteína, campanhas de Pesquisa) — não é o catálogo completo.

## Duas metades da API

| Metade | Como se usa | Efeito |
|---|---|---|
| **Leitura (GAQL)** | `GoogleAdsService.search_stream(customer_id, query)` — um único service pra qualquer `SELECT ... FROM <recurso>` | Nenhum — só consulta |
| **Escrita (mutate)** | Um service por tipo de entidade (`CampaignService`, `AdGroupService`, etc.), cada um com `mutate_*(customer_id, operations)` | Cria/altera/remove de verdade na conta |

Isso já é diferente do GTM: aqui a leitura é **um service só** pra tudo
(`GoogleAdsService`), então dar ao Julio um tool de leitura genérico
(GAQL parametrizado) é natural — não precisa de um tool por recurso.

## O que já usamos hoje

**Leitura** (`collector.py`, GAQL via `GoogleAdsService`):
```
FROM campaign      -- métricas por campanha (últimos 30 dias, fixo)
FROM ad_group       -- métricas por grupo de anúncio
FROM keyword_view   -- métricas por keyword
```

**Escrita** (`campaign_builder.py`, só quando o Julio propõe uma campanha
e o humano confirma):
```
CampaignBudgetService     -- cria o orçamento
CampaignService            -- cria a campanha (sempre PAUSADA)
CampaignCriterionService   -- geo + idioma
AdGroupService              -- cria o grupo de anúncio
AdGroupCriterionService     -- adiciona as keywords
AdGroupAdService             -- cria o anúncio responsivo
```
`executor.py` (pipeline automático agendado, não o Julio) também usa
`CampaignBudgetService`/`AdGroupCriterionService`/`AdGroupService` pra
pausar keyword, ajustar lance e ajustar orçamento — sempre dentro dos
guardrails do `CLAUDE.<site>.md`.

## Recursos de leitura relevantes que NÃO usamos ainda

| Recurso | O que traz | Por que interessa |
|---|---|---|
| `search_term_view` | Termos de busca reais que dispararam o anúncio (diferente da keyword configurada — é o que a pessoa *digitou*) | **Candidato mais forte pra tool novo.** É a base pra decidir negativação de termo — exatamente o tipo de pedido que já apareceu em teste ("pausar essa keyword que gasta sem converter") |
| `campaign_search_term_insight` | Agrupamento/categoria de termos de busca por campanha | Visão mais resumida que `search_term_view` bruto |
| `change_event` / `change_status` | Histórico de mudanças na conta (quem mudou o quê e quando) | Auditoria — equivalente ao `searchChangeHistoryEvents` do GA4 |
| `conversion_action` | O que está configurado como conversão na conta Ads (nome, categoria, se está ativo) | Equivalente ao `conversionEvents`/`keyEvents` do GA4 — confirma se o Ads está contando a conversão certa |
| `recommendation` | Sugestões de otimização que o próprio Google Ads gera (aumentar orçamento, keywords novas, etc.) | Pode virar contexto extra pro Julio comentar, mas cuidado: são sugestões do Google pra gastar mais, não neutras |
| `customer` | Dados da conta (nome, moeda, fuso, status) | Confirmação básica de identidade da conta |
| `customer_client` | Hierarquia de contas dentro da MCC | Só relevante se formos listar/comparar as contas da MCC "IF Apoio" automaticamente — mesma ressalva de auto-descoberta dos outros agentes: não usar pra adivinhar qual conta é qual site |
| `geographic_view` / `location_view` | Performance por localização geográfica | Relevante pro segmento (logística de entrega de carnes/perecíveis, igual já observado na análise de GA4) |
| `ad_group_ad_asset_view` | Performance de cada asset (título/descrição) dentro de um anúncio responsivo | Detalha quais textos específicos convertem melhor |
| `shopping_performance_view` | Performance de campanhas Shopping | Só relevante se algum site vier a rodar Shopping — nenhum roda hoje |

## Fora de escopo (não relevante pro projeto)

`hotel_*`, `travel_*`, `local_services_*`, `keyword_plan_*` (ferramenta de
planejamento de keyword, feature separada de campanha ativa),
`asset_group*` (específico de Performance Max), `you_tube_video_upload`,
`video*`, demografia avançada (`age_range_view`, `gender_view`,
`parental_status_view`, `income_range_view`, `life_event`) e audiências
customizadas (`user_list`, `custom_audience`, `combined_audience`) — nada
disso está em uso em nenhuma das 3 contas hoje.

## Próximo passo natural

Diferente do GTM (onde leitura e escrita são simétricas e a escrita é
sempre arriscada), aqui já existe um precedente de ação segura por padrão:
`propor_campanha` (cria PAUSADA, exige confirmação). Um tool de leitura
`consultar_termos_busca` (GAQL em `search_term_view`, parametrizado por
campanha/período) seria o próximo mais óbvio — resolveria diretamente o
tipo de pedido "essa keyword gasta sem converter" que já apareceu em teste
e foi corretamente registrado em `../agente-julio/pedidos-futuros.md` por
falta dessa capacidade.
