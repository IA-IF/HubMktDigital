# Gap raw → tool.json — SEARCH_CONSOLE

Auditoria de 2026-07-27 (plano
`docs/superpowers/plans/2026-07-27-cobertura-tool-json.md`, Task 4).
Fonte: `raw/discovery.json` (discovery document completo da
`searchconsole` v1) + os 2 `tool.json` já existentes +
`.claude/skills/auditoria-search-console/SKILL.md`.

## Métodos reais (discovery.json)

`searchanalytics.query`, `sitemaps.{list,get,submit,delete}`,
`sites.{list,get,add,delete}`, `urlInspection.index.inspect`,
`urlTestingTools.mobileFriendlyTest.run`.

## O que já tem tool.json

| tool.json | Cobre | Método usado |
|---|---|---|
| `analise_vendas` (`analise_organico`) | Fase C do esquema de vendas: cliques/impressões/CTR/posição, split marca vs genérico, cruzado com GA4 | `searchanalytics.query` |
| `analise_tecnica` | Fase D (só indexação): saúde de sitemaps enviados (processado, erros, páginas descobertas vs indexadas) | `sitemaps.list`/`sitemaps.get` |

## Gap identificado

| Capacidade | Método | Já coberto? | Prioridade |
|---|---|---|---|
| Inspeção de URL individual (indexada? erro? motivo?) | `urlInspection.index.inspect` | **Não** | Média — complementa `analise_tecnica`, que hoje só olha sitemap agregado, não URL a URL |
| Enviar sitemap novo | `sitemaps.submit` | Não | Baixa — CLAUDE.md da skill já marca isso como "fora de escopo hoje (só leitura)"; é escrita, precisa de fluxo de confirmação se virar tool |
| Teste de mobile-friendly | `urlTestingTools.mobileFriendlyTest.run` | Não | Baixa — não citado em nenhum pedido, e Core Web Vitals real (Fase D) já está planejado via Lighthouse/`chrome-devtools-mcp`, não via esta API |
| Gerenciar sites verificados (`sites.add/delete`) | `sites.*` | Não | Baixa — operação de setup único, não recorrente |

## Recomendação

SEARCH_CONSOLE é a plataforma com **menor gap real** das 4 auditadas —
as duas capacidades de leitura mais usadas (tráfego orgânico, saúde de
sitemap) já têm tool.json. O único item que vale considerar pra Fase 2
é `urlInspection.index.inspect` como uma tool de leitura pontual
(diagnóstico de "por que essa URL específica não está indexando"), útil
quando `analise_tecnica` apontar páginas descobertas-mas-não-indexadas e
precisar de detalhe por URL. `sitemaps.submit` só vira tool quando (se)
alguém decidir que o agente pode fazer ação de escrita em Search
Console — hoje é decisão explicitamente adiada.
