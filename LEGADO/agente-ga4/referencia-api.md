# Referência — o que a API do GA4 oferece (e o que a gente usa hoje)

Levantado direto do discovery document ao vivo das duas APIs (via
`googleapiclient.discovery.build(...)._rootDesc`, não da memória), em
2026-07-22. Objetivo: ter em mãos o catálogo completo antes de decidir quais
métodos valem virar tools do Julio — puxando a mesma lição do `agente-ads`
(dar acesso de leitura real em vez do LLM ficar perguntando sem poder agir).

## Biblioteca e autenticação

```python
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

creds = Credentials(token=None, scopes=SCOPES, **config.ga4_credentials_config())
service = build(nome_api, versao, credentials=creds, cache_discovery=False)
```

- `google-api-python-client` — cliente **generico** por discovery document,
  não tem classe fixa por API. `build(nome, versao, ...)` devolve um objeto
  `Resource` cujos métodos são gerados dinamicamente a partir do discovery
  doc (é por isso que não tem autocomplete/typing nativo — os métodos só
  existem em runtime).
- `google-auth` (`google.oauth2.credentials.Credentials`) — carrega
  client_id/secret/refresh_token do `.env.<site>` e renova o access token
  sozinho a cada chamada.
- Scope hoje: `https://www.googleapis.com/auth/analytics.readonly` — **só
  leitura**. Qualquer método de escrita (create/patch/delete abaixo) exige
  trocar para `analytics.edit` (ou `analytics.manage.users` pros de
  usuário), que é uma decisão de escopo maior — não é so mudar 1 linha, é
  decidir se o agente pode alterar configuração de propriedade GA4 de
  verdade.

## As duas APIs

| API | Versão | Pra que serve | Usada hoje em |
|---|---|---|---|
| **Analytics Admin API** (`analyticsadmin`) | v1beta | Configuração da propriedade: eventos de conversão, data streams, custom dimensions/metrics, links com Google Ads, retenção de dados | `ga4_auditor._eventos_conversao` |
| **Analytics Data API** (`analyticsdata`) | v1beta | Consultar os dados coletados (relatórios, tempo real, funil, pivot) | `ga4_auditor._contagem_eventos_funil` |

## O que `ga4_auditor.py` usa hoje (2 de ~50 métodos disponíveis)

```python
service.properties().conversionEvents().list(parent=property_path)   # Admin API
service.properties().runReport(property=property_path, body={...})   # Data API
```

**Achado à parte, não relacionado ao Julio:** `conversionEvents` está
**deprecated** no discovery doc — a própria Google recomenda migrar pra
`keyEvents` (`properties.keyEvents.list/create/get/patch/delete`), que é o
sucessor. Ainda funciona, mas vale trocar em algum momento pra não quebrar
quando a Google descontinuar de vez.

## Catálogo completo — Admin API (`analyticsadmin`, v1beta)

Leitura (candidatos naturais pra tools do Julio, mesmo padrão do
`--relatorio` do agente-ads: não mexem em nada, só respondem):

| Método | Requer | O que traz |
|---|---|---|
| `accountSummaries.list` | — | Visão resumida de todas as contas + propriedades acessíveis (bom ponto de entrada se o Julio precisar descobrir property_id sem estar no `.env`) |
| `accounts.get` / `accounts.list` | `name` / — | Dados da conta |
| `accounts.getDataSharingSettings` | `name` | Configuração de compartilhamento de dados |
| `properties.get` | `name` | Metadados da propriedade (nome, fuso, moeda, data de criação) |
| `properties.list` | — | Propriedades filhas de uma conta |
| `properties.conversionEvents.list` / `.get` | `parent` / `name` | **(deprecated, ver acima)** Eventos marcados como conversão |
| `properties.keyEvents.list` / `.get` | `parent` / `name` | Sucessor de conversionEvents — mesma info |
| `properties.customDimensions.list` / `.get` | `parent` / `name` | Dimensões customizadas configuradas |
| `properties.customMetrics.list` / `.get` | `parent` / `name` | Métricas customizadas configuradas |
| `properties.dataStreams.list` / `.get` | `parent` / `name` | Data streams (é aqui que mora o `measurement_id` — dá pra confirmar sem depender do `.env`) |
| `properties.dataStreams.measurementProtocolSecrets.list` | `parent` | Secrets do Measurement Protocol (server-side tracking) |
| `properties.firebaseLinks.list` | `parent` | Link com Firebase, se houver |
| `properties.googleAdsLinks.list` | `parent` | **Interessante:** confirma se a propriedade GA4 está linkada à conta certa do Google Ads — dá pra auditar isso automaticamente em vez de assumir |
| `properties.getDataRetentionSettings` | `name` | Prazo de retenção de dados de usuário configurado |
| `accounts.runAccessReport` / `properties.runAccessReport` | `entity` | Quem acessou os dados de relatório e quando (auditoria de acesso, não de tráfego) |
| `accounts.searchChangeHistoryEvents` | `account` | Histórico de mudanças de configuração na conta — útil pra "o que mudou desde a última auditoria" |

Escrita (create/patch/delete de conversionEvents, customDimensions,
customMetrics, dataStreams, googleAdsLinks, firebaseLinks, e
`properties.create`/`.delete`/`.patch` pra propriedade inteira) — **exigem
scope `analytics.edit`**, não cobertos aqui de propósito. Ficam pra uma
decisão separada do usuário sobre até onde o agente pode alterar
configuração de tracking.

## Catálogo completo — Data API (`analyticsdata`, v1beta)

| Método | Requer | O que traz |
|---|---|---|
| `properties.runReport` | `property` | Relatório padrão (dimensões x métricas, período configurável) — **já usado** pro funil de 7 dias |
| `properties.batchRunReports` | `property` | Várias `runReport` numa chamada só (economiza round-trips se o Julio precisar de vários cortes ao mesmo tempo) |
| `properties.runRealtimeReport` | `property` | Dados dos últimos ~30 minutos — útil pra "está entrando tráfego AGORA" (ex.: confirmar que uma campanha nova está gerando visitas) |
| `properties.runPivotReport` / `batchRunPivotReports` | `property` | Relatório pivotado (cruzamento tipo tabela dinâmica) — mais poderoso que runReport pra análises multi-dimensão |
| `properties.getMetadata` | `name` | Lista TODAS as dimensões e métricas disponíveis pra essa propriedade — útil pra descobrir nomes válidos antes de montar um `runReport` dinâmico |
| `properties.checkCompatibility` | `property` | Verifica se uma combinação de dimensões/métricas é válida antes de rodar o relatório de verdade (evita erro 400) |
| `properties.audienceExports.*` | `parent`/`name` | Cria e consulta exports de audiência (lista de usuários) — caso de uso mais avançado, não prioridade agora |

## Pra decidir depois (não implementado ainda)

- Se o Julio ganhar um tool de GA4, o candidato óbvio é `runReport`
  (parametrizado por período/dimensões/métricas) — mesmo padrão do
  `consultar_desempenho` planejado pro agente-ads.
- `properties.googleAdsLinks.list` daria pra virar uma checagem automática
  no `ga4_auditor.py` (hoje o link Ads↔GA4 não é verificado, só assumido).

**Rejeitado de propósito:** usar `accountSummaries.list` /
`properties.dataStreams.list` pra auto-descobrir o property_id e eliminar
os IDs fixos do `.env.<site>`. Decisão do usuário (2026-07-22): o Julio
trata **um site por conversa, sempre por seleção explícita** (comando
`/site`, nunca inferência automática) — é o mesmo motivo que fez a gente
tirar o `SITE` de env var do Julio e virar pergunta obrigatória na
conversa (ver `../agente-julio/README.md`). Auto-descoberta de propriedade
reintroduziria exatamente o risco que essa decisão evitou: o agente
adivinhar o site errado sozinho. Os IDs no `.env.<site>` continuam sendo a
fonte de verdade de qual conta cada slug de site aponta.
