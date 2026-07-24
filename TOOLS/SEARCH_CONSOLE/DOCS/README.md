# Search Console — dado bruto coletado (2026-07-22)

Sem curadoria — quem digere isso é uma etapa futura (Redis/embeddings, ver
`inteligencia.md` Etapa 2).

## Arquivos

- `raw/discovery.json` — discovery document inteiro da `searchconsole`
  v1: `searchanalytics`, `sitemaps`, `sites`, `urlInspection`,
  `urlTestingTools`, cada método com descrição completa e schema de
  parâmetros/request/response, sem cortar nada.

## Como foi coletado

```python
service = build("searchconsole", "v1", credentials=creds, cache_discovery=False)
service._rootDesc  # discovery document cru
```

Credenciais: `.env` da raiz (`SC_CLIENT_ID`/`SC_CLIENT_SECRET`/
`SC_REFRESH_TOKEN`) — nunca `LEGADO/`.

## O que NÃO tem aqui

Nenhuma tabela resumida, nenhum "isso é interessante". Ver
`.claude/skills/learn-api/SKILL.md` pro motivo.
