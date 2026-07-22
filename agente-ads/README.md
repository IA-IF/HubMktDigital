# Agente Ads — multi-site

Réplica do `agente-cmo` (`C:\INTEGRAFOODS\teste\GADS\agente-cmo`, mantido
intocado como referência), adaptada pra multi-site: coleta métricas do
Google Ads, analisa com o Claude, executa otimizações dentro de guardrails
e envia relatório diário — para qualquer site cadastrado via `.env.<SITE>`.
Ver `../pratico.md` (item 4) e `../brainstorm.md` para o contexto maior do
projeto.

Sites conectados hoje: **integrafoods** (`.env.integrafoods`, conta
"Integra Foods V2" `332-316-6484`) e **3gfoods** (`.env.3gfoods`, conta
"3G Foods" `758-019-9564`, já com campanha ativa). Ambos na MCC `890-192-5637`
"IF Apoio".

## Multi-site

`config.py` carrega `.env.<SITE>` e `CLAUDE.<SITE>.md` (variável de ambiente
`SITE`, ex: `SITE=3gfoods python main.py --testar-conexao`). Sem `SITE`,
usa `integrafoods`. Pra conectar um site novo, siga
`../.claude/skills/onboard-site/SKILL.md` em vez de repetir o setup manualmente.

## Fluxo

```
collector.py (Google Ads API, GAQL, 30 dias)
   -> analyst.py (Claude + regras do CLAUDE.<SITE>.md -> JSON de acoes)
   -> executor.py (guardrails + fila de aprovacao + Google Ads API)
   -> reporter.py (relatorio em logs/<SITE>/ + Slack/e-mail opcionais)
```

## Setup de um site (ex: `.env.integrafoods`)

1. `pip install -r requirements.txt`
2. Copie `.env.example` para `.env.<SITE>`. Preencha `GOOGLE_ADS_CUSTOMER_ID`
   e `GOOGLE_ADS_LOGIN_CUSTOMER_ID` (login_customer_id é o mesmo pra qualquer
   site da mesma MCC). Copie `GOOGLE_ADS_DEVELOPER_TOKEN`, `GOOGLE_ADS_CLIENT_ID`,
   `GOOGLE_ADS_CLIENT_SECRET` e `GOOGLE_ADS_REFRESH_TOKEN` de um `.env.<outro-site>`
   já configurado (mesma MCC, mesmo projeto Cloud — refresh_token de usuário
   não é por conta específica, costuma funcionar direto) — só preencher
   `ANTHROPIC_API_KEY` é novo por site (ou reaproveitar a mesma).
3. Se o refresh_token copiado não tiver acesso à conta nova, gere um novo:
   `SITE=<site> python generate_refresh_token.py` (copie a saída para o `.env.<SITE>`).
4. Copie `CLAUDE.<outro-site>.md` como ponto de partida e ajuste os valores
   marcados com **(AJUSTAR)** (ticket médio, margem, orçamento mensal) ao
   negócio real desse site.
5. Teste a conexão: `SITE=<site> python main.py --testar-conexao`

## Uso

| Comando | O que faz |
|---|---|
| `SITE=<site> python main.py --dry-run` | Analisa e recomenda, **não altera nada** (padrão) |
| `SITE=<site> python main.py --executar` | Executa ações aprovadas pelos guardrails |
| `SITE=<site> python main.py --testar-conexao` | Lista campanhas ativas para validar credenciais |
| `SITE=<site> python main.py --criar-campanha` | Cria campanha a partir de um JSON no stdin (chamado pelo `../agente-julio`, nao interativo) |

O bot conversacional (Telegram, LLM perguntando o que falta pra montar a
campanha) mora em `../agente-julio` — este modulo so expõe a capacidade de
criar a campanha via `--criar-campanha`, sem saber quem está do outro lado.

Ações bloqueadas pelos guardrails vão para `data/<SITE>/aprovacoes_pendentes.json` —
revise e aplique manualmente (ou aprove e reexecute).

## Segurança — não pule!

- **Semanas 1–2:** só `--dry-run`; compare as recomendações com o que você faria.
- **Semanas 3–4:** execute manualmente as ações da fila que você aprovar.
- **Mês 2+:** `--executar` para ações de baixo risco; orçamento continua exigindo aprovação (guardrail `LIMITE_APROVACAO_DIARIO`).

## Status

**Conectado nos 2 sites.** `integrafoods`: `--testar-conexao` confirmado
(22/07/2026) — sem campanhas ainda (conta nova). `3gfoods`: `--testar-conexao`
confirmado (22/07/2026) — já com 1 campanha ativa (`23700278085`). Falta
ajustar os valores `(AJUSTAR)` dos `CLAUDE.<site>.md` com dados reais do
negócio antes do primeiro `--dry-run` de qualquer um dos dois.
