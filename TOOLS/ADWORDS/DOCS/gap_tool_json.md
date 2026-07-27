# Gap raw → tool.json — ADWORDS

Auditoria de 2026-07-27 (plano
`docs/superpowers/plans/2026-07-27-cobertura-tool-json.md`, Task 2).
Fonte: `raw/services.json` (112 serviços reais da lib `google-ads` v24) +
os 2 `tool.json` já existentes + o spec já aprovado
`docs/superpowers/specs/2026-07-24-skag-ads-negative-keywords-design.md`.

## O que já tem tool.json

| tool.json | Cobre | Serviços usados |
|---|---|---|
| `analise_vendas` (`analise_ads`) | Eficiência de investimento (custo x conversão x GA4), Fase B do esquema de vendas | `GoogleAdsService` (GAQL) |
| `criar_campanha` | Criação de campanha Search completa, sempre pausada, com confirmação obrigatória (`requer_confirmacao: true`) | Implícito: `campaign_service`, `campaign_budget_service`, `ad_group_service`, `ad_group_criterion_service` (keywords), `ad_group_ad_service` |

## Gap identificado (contra `services.json`)

| Capacidade | Serviço real | Já coberto? | Evidência de demanda | Prioridade |
|---|---|---|---|---|
| Negative keywords (lista universal + shared set) | `shared_set_service`, `shared_criterion_service`, `campaign_shared_set_service` | **Não** | Sim — já é objetivo 2 do spec SKAG aprovado (`2026-07-24-skag-ads-negative-keywords-design.md`), "pronto pra virar plano de implementação" | **Alta** |
| Estrutura SKAG real (`criar_campanha` hoje cria 1 grupo com N keywords, viola 1 keyword = 1 grupo) | mesmos serviços de `criar_campanha`, uso diferente | Parcial — a tool existe mas não segue o padrão SKAG ainda | Sim — objetivo 1 do mesmo spec | **Alta** |
| Ajustar/pausar/ativar campanha existente | `campaign_service` (mutate) | Não | Não tem spec ainda, mas é operação básica de gestão | Média |
| Conversões (criar/consultar evento de conversão) | `conversion_action_service` | Não | Citado em `elis.md` ("criação de novas entradas... conversões") como parte do que falta pra "completar os serviços do Google" | Média |
| Públicos/audiências | `audience_service`, `custom_audience_service` | Não | Mesma citação em `elis.md` — "públicos" | Média |
| Estratégia de lances (bidding strategy) | `bidding_strategy_service` | Não | Não tem demanda explícita registrada ainda | Baixa |

## Recomendação

Não criar `tool.json` novo agora — a Fase 2 (fora deste plano) já tem
prioridade clara: **`negative_keywords`** e o ajuste de `criar_campanha`
pra estrutura SKAG de verdade são exatamente o que o spec
`2026-07-24-skag-ads-negative-keywords-design.md` já descreve e está
"aprovado, pronto pra virar plano de implementação" — não precisa de
levantamento novo, só falta a Fase 2 virar plano executável em cima do
spec que já existe.

Públicos/segmentação/conversões (citados em `elis.md`) ficam Média — têm
serviço real confirmado (`audience_service`, `conversion_action_service`)
mas nenhum spec ainda; alimentam o plano
`2026-07-27-pesquisa-tecnica-perfil-cliente.md` (Frente 2) quando essa
pesquisa rodar.
