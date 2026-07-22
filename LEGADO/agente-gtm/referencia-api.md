# Referência — o que a API do GTM oferece (e o que a gente usa hoje)

Mesmo processo do `agente-ga4/referencia-api.md`: levantado direto do
discovery document ao vivo (`googleapiclient.discovery.build('tagmanager',
'v2', ...)._rootDesc`), em 2026-07-22. Objetivo: dar ao Julio contexto pra
decidir quais métodos virar tools, sem ele ter que adivinhar o que a API
suporta.

## Biblioteca e autenticação

Igual ao GA4 — `google-api-python-client` + `google-auth`, scope hoje **so
leitura**: `https://www.googleapis.com/auth/tagmanager.readonly`. A
diferença importante em relação ao GA4: o GTM é fundamentalmente uma
ferramenta de **configuração** (tags, triggers, variáveis), não de
relatório — a maioria dos métodos do catálogo é escrita (create/update/
delete/publish), não leitura. Isso muda o cálculo de risco: dar ao Julio
capacidade de leitura no GTM é tão seguro quanto no GA4, mas qualquer
capacidade de escrita aqui significa **alterar o que dispara no site em
produção** — categoria de decisão bem mais sensível que "criar campanha
pausada" (que já exige confirmação humana).

## Hierarquia de recursos

```
accounts
  └── containers
        ├── environments, destinations, versions (version_headers, live)
        └── workspaces  (workspace = "rascunho" onde as edições acontecem)
              ├── tags, triggers, variables, built_in_variables
              ├── folders, zones, clients, templates, transformations
              ├── gtag_config (config do "Google tag" unificado, ver achado no pratico.md)
              └── getStatus, sync, resolve_conflict, quick_preview, create_version
accounts.user_permissions
```

`create_version` + `versions.publish` é o par de métodos que efetivamente
"publica pro site" — qualquer coisa antes disso fica só no workspace
(rascunho), sem afetar produção. Isso é a mesma distinção "live vs draft"
que o `gtm_auditor.py` já audita hoje.

## O que `gtm_auditor.py` usa hoje (5 de ~50 métodos)

```python
service.accounts().containers().get(path=container_path)
service.accounts().containers().workspaces().list(parent=container_path)
service.accounts().containers().workspaces().tags().list(parent=workspace_path)
service.accounts().containers().workspaces().triggers().list(parent=workspace_path)
service.accounts().containers().workspaces().variables().list(parent=workspace_path)
service.accounts().containers().versions().live(parent=container_path)
```

Todos leitura. Não usa `gtag_config` diretamente — o achado do "Google tag"
com measurement ID divergente (ver `pratico.md`, 3G Foods) foi encontrado
inspecionando `tags` do tipo `googtag`, não via `gtag_config.list` — vale
considerar trocar pra essa API dedicada, que provavelmente é a fonte mais
direta desse dado.

## Catálogo — candidatos a tool de leitura pro Julio

| Método | Requer | O que traz |
|---|---|---|
| `accounts.list` / `accounts.get` | — / `path` | Contas GTM acessíveis — **rejeitado usar pra auto-descoberta** (mesma regra do GA4: site sempre por seleção explícita, não inferência) |
| `containers.list` / `.get` | `parent` / `path` | Containers de uma conta |
| `containers.snippet` | `path` | Devolve o HTML/JS de instalação do container — útil pra confirmar se o snippet no site bate com o esperado |
| `containers.lookup` | — (query por destination/tag ID) | Acha o container dono de um Measurement ID/tag — poderia confirmar automaticamente vínculos GA4↔GTM |
| `workspaces.list` / `.get` / `.getStatus` | `parent` / `path` / `path` | Workspace ativo e se há conflitos/mudanças pendentes de sincronizar |
| `workspaces.tags.list` / `.get` | `parent` / `path` | **já usado** |
| `workspaces.triggers.list` / `.get` | `parent` / `path` | **já usado** |
| `workspaces.variables.list` / `.get` | `parent` / `path` | **já usado** |
| `workspaces.built_in_variables.list` | `parent` | Variáveis embutidas habilitadas (Click URL, Page Path, etc.) — não auditado hoje |
| `workspaces.gtag_config.list` / `.get` | `parent` / `path` | Config do Google tag unificado — candidato a substituir a inspeção manual de tags tipo `googtag` |
| `workspaces.folders.list` / `.entities` | `parent` / `path` | Organização do container em pastas |
| `workspaces.zones.list` | `parent` | Zonas (containers aninhados/parciais) — pouco provável de existir nas contas atuais |
| `version_headers.list` / `.latest` | `parent` | Histórico de versões publicadas — dá pra checar "quando foi a última publicação" sem baixar a versão inteira |
| `versions.live` | `parent` | **já usado** — versão publicada atualmente |
| `versions.get` | `path` | Detalhe de uma versão específica do histórico |
| `accounts.user_permissions.list` | `parent` | Quem tem acesso à conta GTM — auditoria de acesso, mesmo espírito do `accounts.runAccessReport` do GA4 |

## Escrita — fora de escopo por enquanto

Tudo que é `create`/`update`/`delete`/`revert` pra tags, triggers,
variáveis, templates, etc., mais `workspaces.create_version` +
`versions.publish` (o ato de publicar pro site). Diferente da Ads (onde
"criar campanha pausada" já é uma ação de baixo risco bem definida), aqui
não existe um equivalente óbvio de "ação segura por padrão" — qualquer
mudança de tag published afeta tracking em produção imediatamente. Se/quando
decidirmos dar ao Julio capacidade de propor mudança de GTM, o modelo
correto provavelmente é: criar no **workspace** (rascunho, não afeta nada)
e parar aí — nunca chamar `versions.publish` automaticamente, sempre exigir
que um humano publique manualmente depois de revisar no próprio GTM.

## Próximo passo natural

Um tool `consultar_gtm` nos moldes do `consultar_trafego` (leitura,
resposta imediata) cobriria bem: resumo do container (tags/triggers/
variáveis, se tem mudança não publicada), snippet de instalação, e
`gtag_config` pra checar o vínculo com GA4/Ads automaticamente — sem
nenhuma capacidade de escrita.
