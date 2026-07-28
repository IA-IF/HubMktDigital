# Google Ads — dado bruto coletado (2026-07-22, atualizado 2026-07-27)

Sem curadoria — quem digere isso é uma etapa futura (Redis/embeddings, ver
`inteligencia.md` Etapa 2). Este README só diz onde cada coisa está.

## Arquivos (coleta 2026-07-22 — leitura/GAQL)

- `raw/google_ads_fields.json` — **3.050 registros**, um por campo GAQL
  real da conta (via `GoogleAdsFieldService.search_google_ads_fields`,
  sem `WHERE`/`FROM`, esse serviço não aceita `FROM`). Cada registro tem
  `name`, `category` (ATTRIBUTE/METRIC/SEGMENT/RESOURCE), `data_type`,
  `selectable`, `filterable`, `sortable`, `is_repeated`,
  `selectable_with` (outros campos combináveis no mesmo `SELECT`),
  `metrics`/`segments` (quando o campo é um RESOURCE, quais métricas/
  segmentos ele aceita), `enum_values`.
- `raw/services.json` — **112 nomes**, um por serviço `*_service`
  instalado de verdade na lib `google-ads` v24 (`pkgutil`/`os.listdir` no
  pacote `google.ads.googleads.v24.services.services`, não é lista de
  memória).

Como foi coletado:
```python
client = GoogleAdsClient.load_from_dict(cfg)  # credenciais de .env (raiz) + SITES/<site>/.env
gaf = client.get_service("GoogleAdsFieldService")
resp = gaf.search_google_ads_fields(query="SELECT name, category, data_type, selectable, filterable, sortable, selectable_with, metrics, segments, enum_values, is_repeated")
```
Credenciais: `.env` da raiz (`GOOGLE_ADS_*` compartilhado) +
`SITES/3gfoods/.env` (`GOOGLE_ADS_CUSTOMER_ID`) — nunca `LEGADO/`.

## Arquivos (coleta 2026-07-27 — mutate/escrita)

A coleta acima cobre só o lado de LEITURA (GAQL/relatório) — nada sobre
como CRIAR/ALTERAR recursos (o que `TOOLS/ADWORDS/criar_campanha/`
realmente faz). Essa API não tem discovery document em runtime (é
gRPC/protobuf gerado) — a fonte mais completa e autoritativa é o
próprio pacote `google-ads` instalado (v31.1.0, API v24), via reflection
protobuf direto nos módulos gerados (sem precisar de credencial/rede —
só introspecção de schema).

- `raw/mutate_mensagens.json` — schema completo (todos os campos, com
  `name`/`number`/`type`/`label`/`message_type`/`enum_type`+
  `enum_values`/`oneof` quando aplicável) de 27 mensagens usadas na
  criação de campanha: `Campaign`, `CampaignOperation`,
  `MutateCampaignsRequest/Response`, `CampaignBudget`+`Operation`,
  `AdGroup`+`Operation`, `AdGroupCriterion`+`Operation`, `KeywordInfo`,
  `AdGroupAd`+`Operation`, `Ad`, `ResponsiveSearchAdInfo`, `AdTextAsset`,
  `CampaignCriterion`+`Operation`, `MutateOperation`+`Response`,
  `GoogleAdsError`, `GoogleAdsFailure`.
- `raw/mutate_servicos.json` — todo método público de
  `CampaignService`, `CampaignBudgetService`, `AdGroupService`,
  `AdGroupCriterionService`, `AdGroupAdService`,
  `CampaignCriterionService`, `GoogleAdsService`, com assinatura
  completa + docstring inteiro (o docstring do client gerado É o texto
  oficial da API, extraído do `.proto` fonte).

Como foi coletado (sem credencial nenhuma — só reflection de schema):
```python
import importlib, pkgutil
import google.ads.googleads.v24 as v24_pkg
# 1) indexar toda classe de mensagem em **/types/*.py (proto-plus: o
#    DESCRIPTOR fica atras de Classe.pb().DESCRIPTOR, nao direto)
for _, nome_modulo, _ in pkgutil.walk_packages(v24_pkg.__path__, prefix="google.ads.googleads.v24."):
    if ".types" in nome_modulo:
        mod = importlib.import_module(nome_modulo)
        # ... ver TOOLS/ADWORDS/DOCS/raw/ script no historico do plano de arquitetura

# 2) servicos: introspectar o modulo <servico>.client, metodos publicos
#    com inspect.signature + inspect.getdoc (docstring gerado do .proto)
mod = importlib.import_module("google.ads.googleads.v24.services.services.campaign_service.client")
```

## O que NÃO tem aqui

Nenhuma seleção de "campos relevantes", nenhum exemplo de GAQL/mutate
pronto, nenhuma explicação de quando usar o quê. De propósito — ver
`.claude/skills/learn-api/SKILL.md` pro motivo.
