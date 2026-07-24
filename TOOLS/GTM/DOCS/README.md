# GTM — dado bruto coletado (2026-07-22)

Sem curadoria — quem digere isso é uma etapa futura (Redis/embeddings, ver
`inteligencia.md` Etapa 2).

## Arquivos

- `raw/discovery.json` — discovery document inteiro da `tagmanager` v2:
  todos os recursos (account, container, environment, version, workspace
  e as 10 entidades dentro dele — tags, triggers, variables, folders,
  templates, transformations, zones, clients, built_in_variables,
  gtag_config —, destinations, user_permissions), cada método com
  descrição completa e schema de parâmetros/request/response, sem cortar
  nada.

## Como foi coletado

```python
service = build("tagmanager", "v2", credentials=creds, cache_discovery=False)
service._rootDesc  # discovery document cru
```

Credenciais: `.env` da raiz (`GTM_CLIENT_ID`/`GTM_CLIENT_SECRET`/
`GTM_REFRESH_TOKEN`) — nunca `LEGADO/`.

## O que NÃO tem aqui

Nenhuma tabela resumida por grupo de entidade, nenhum "isso é
interessante". Ver `.claude/skills/learn-api/SKILL.md` pro motivo.
