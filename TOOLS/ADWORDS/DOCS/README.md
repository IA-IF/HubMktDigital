# Google Ads — dado bruto coletado (2026-07-22)

Sem curadoria — quem digere isso é uma etapa futura (Redis/embeddings, ver
`inteligencia.md` Etapa 2). Este README só diz onde cada coisa está.

## Arquivos

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

## Como foi coletado

```python
client = GoogleAdsClient.load_from_dict(cfg)  # credenciais de .env (raiz) + SITES/<site>/.env
gaf = client.get_service("GoogleAdsFieldService")
resp = gaf.search_google_ads_fields(query="SELECT name, category, data_type, selectable, filterable, sortable, selectable_with, metrics, segments, enum_values, is_repeated")
```

Credenciais: `.env` da raiz (`GOOGLE_ADS_*` compartilhado) +
`SITES/3gfoods/.env` (`GOOGLE_ADS_CUSTOMER_ID`) — nunca `LEGADO/`.

## O que NÃO tem aqui

Nenhuma seleção de "campos relevantes", nenhum exemplo de GAQL pronto,
nenhuma explicação de quando usar o quê. De propósito — ver
`.claude/skills/learn-api/SKILL.md` pro motivo.
