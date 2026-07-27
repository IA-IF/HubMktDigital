# Gap raw → tool.json — GTM

Auditoria de 2026-07-27 (plano
`docs/superpowers/plans/2026-07-27-cobertura-tool-json.md`, Task 1).
Fonte: `raw/discovery.json` (discovery document completo da
`tagmanager` v2) + `.claude/skills/auditoria-gtm/SKILL.md`.

**Situação hoje: zero `tool.json` em `TOOLS/GTM/`.** O único jeito de ler
GTM hoje é `auditoria-gtm`, que é wrapper de `LEGADO/agente-gtm/main.py`
— fora da arquitetura nova (`TOOLS/`), não indexável pelo `discover_tool`
(que só indexa `TOOLS/**/tool.json`, ver
`TOOLS/GOOGLE_API/discover_tool_indexar.py:46-52`).

## Recursos do container GTM (discovery.json)

Grupos de entidade dentro de um `workspace`: `tags`, `triggers`,
`variables`, `folders`, `templates`, `transformations`, `zones`,
`clients`, `built_in_variables`, `gtag_config`. Fora do workspace:
`account`, `container`, `environment`, `version`, `destination`,
`user_permission`.

| Capacidade (grupo GTM) | Já lida por algo hoje? | Tem `tool.json`? | Prioridade |
|---|---|---|---|
| `tags` (list/get) | Sim — `auditoria-gtm --auditar` (via LEGADO) | Não | **Alta** |
| `triggers` (list/get) | Sim — `auditoria-gtm --auditar` (via LEGADO) | Não | **Alta** |
| `variables` sem trigger (list/get) | Sim — `auditoria-gtm --auditar` (via LEGADO) | Não | **Alta** |
| dataLayer/hits GA4 reais (dinâmico) | Sim — `auditoria-gtm --auditar-dinamico` (Playwright, via LEGADO) | Não | Média |
| `version`/`versions.publish` | Não | Não | Baixa (escrita — fora de escopo, ver nota abaixo) |
| `environment` | Não | Não | Baixa |
| `templates`, `transformations`, `zones`, `clients`, `built_in_variables`, `gtag_config` | Não | Não | Baixa (não usados nos fluxos de auditoria hoje) |
| `destination`, `user_permission` | Não | Não | Baixa (não é dado de marketing) |
| `account`, `container` (metadados) | Implícito (precisa do ID pra tudo acima) | Não | Média (pré-requisito das tools de Alta) |

## Recomendação

O primeiro `tool.json` a criar é **`listar_tags_triggers`**
(goal-oriented: "estado atual de tags/triggers/variáveis do container
GTM de um site" — não "chamar `tags.list`"), reimplementado direto
contra a API `tagmanager` v2 em `TOOLS/GTM/`, **não** como wrapper do
`LEGADO/agente-gtm` — CLAUDE.md já marca `LEGADO/` como "código
funcional, mas será substituída". Isso cobre a parte estática de
`auditoria-gtm --auditar` (tags, triggers, variáveis) na arquitetura
nova, e é o que falta pra `discover_tool` conseguir achar GTM quando o
usuário pedir algo relacionado.

A parte dinâmica (`--auditar-dinamico`, Playwright) fica pra depois —
não é `runReport`-like (só leitura de API), é uma auditoria mais pesada,
melhor como uma segunda tool separada quando a primeira estiver
validada.

Escrita (`versions.publish`, editar tags) fica fora desta fase — a
skill `auditoria-gtm` já documenta isso como capacidade separada, ainda
não construída, com guardrail próprio necessário (workspace/rascunho,
publish sempre manual).
