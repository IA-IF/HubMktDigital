# GA4 — dado bruto coletado (2026-07-22)

Sem curadoria — quem digere isso é uma etapa futura (Redis/embeddings, ver
`inteligencia.md` Etapa 2).

## Arquivos

- `raw/admin_discovery.json` — discovery document inteiro da
  `analyticsadmin` v1beta (todos os recursos/métodos/parâmetros/schemas,
  sem cortar descrição nem filtrar método).
- `raw/data_discovery.json` — discovery document inteiro da
  `analyticsdata` v1beta.
- `raw/metadata_3gfoods.json` — resultado completo de
  `properties.getMetadata` pra propriedade da 3G Foods (`514973832`): 376
  dimensões + 140 métricas, cada uma com `apiName`, `uiName`,
  `description`, `category` (e `type`/`expression` quando aplicável).
  **Específico da propriedade** — Integra Foods/Adoro podem ter custom
  dimensions/metrics diferentes; refazer por site se precisar.

## Como foi coletado

```python
service = build("analyticsadmin", "v1beta", credentials=creds, cache_discovery=False)
service._rootDesc  # discovery document cru

service2 = build("analyticsdata", "v1beta", credentials=creds, cache_discovery=False)
service2.properties().getMetadata(name=f"{property_path}/metadata").execute()
```

Credenciais: `.env` da raiz (`GA4_CLIENT_ID`/`GA4_CLIENT_SECRET`/
`GA4_REFRESH_TOKEN`) + `SITES/3gfoods/.env` (`GA4_PROPERTY_ID`) — nunca
`LEGADO/`.

## O que NÃO tem aqui

Nenhuma tabela resumida, nenhum "isso é interessante", nenhum exemplo de
`runReport` pronto. Ver `.claude/skills/learn-api/SKILL.md` pro motivo.
