# Agente Ads — Integra Foods

Réplica do `agente-cmo` (`C:\INTEGRAFOODS\teste\GADS\agente-cmo`, mantido
intocado como referência) configurada para a conta **Integra Foods V2**
(`332-316-6484`, MCC `890-192-5637` "IF Apoio") em vez da 3G Foods. Coleta
métricas do Google Ads, analisa com o Claude, executa otimizações dentro de
guardrails e envia relatório diário. Ver `../pratico.md` (item 4) e
`../brainstorm.md` para o contexto maior do projeto.

## Fluxo

```
collector.py (Google Ads API, GAQL, 30 dias)
   -> analyst.py (Claude + regras do CLAUDE.md -> JSON de acoes)
   -> executor.py (guardrails + fila de aprovacao + Google Ads API)
   -> reporter.py (relatorio em logs/ + Slack/e-mail opcionais)
```

## Setup

1. `pip install -r requirements.txt`
2. Copie `.env.example` para `.env`. `GOOGLE_ADS_CUSTOMER_ID` e
   `GOOGLE_ADS_LOGIN_CUSTOMER_ID` já vêm preenchidos (conta Integra Foods V2 /
   MCC IF Apoio). Copie `GOOGLE_ADS_DEVELOPER_TOKEN`, `GOOGLE_ADS_CLIENT_ID`,
   `GOOGLE_ADS_CLIENT_SECRET` e `GOOGLE_ADS_REFRESH_TOKEN` do `.env` real do
   `agente-cmo` (mesma MCC, mesmo projeto Cloud) — só preencher
   `ANTHROPIC_API_KEY` é novo.
3. Se o refresh_token copiado não tiver acesso à conta nova, gere um novo:
   `python generate_refresh_token.py` (copie a saída para o `.env`).
4. Edite o `CLAUDE.md` — ajuste os valores marcados com **(AJUSTAR)**
   (ticket médio, margem, orçamento mensal) ao negócio real do Integra Foods.
5. Teste a conexão: `python main.py --testar-conexao`

## Uso

| Comando | O que faz |
|---|---|
| `python main.py --dry-run` | Analisa e recomenda, **não altera nada** (padrão) |
| `python main.py --executar` | Executa ações aprovadas pelos guardrails |
| `python main.py --testar-conexao` | Lista campanhas ativas para validar credenciais |
| `python main.py --telegram-bot` | Bot conversacional p/ criar campanhas novas via Telegram |

Ações bloqueadas pelos guardrails vão para `aprovacoes_pendentes.json` —
revise e aplique manualmente (ou aprove e reexecute).

## Segurança — não pule!

- **Semanas 1–2:** só `--dry-run`; compare as recomendações com o que você faria.
- **Semanas 3–4:** execute manualmente as ações da fila que você aprovar.
- **Mês 2+:** `--executar` para ações de baixo risco; orçamento continua exigindo aprovação (guardrail `LIMITE_APROVACAO_DIARIO`).

## Status

Código replicado do `agente-cmo` (22/07/2026), ainda não configurado — falta
preencher o `.env` (passo 2-3 do setup) e os valores `(AJUSTAR)` do
`CLAUDE.md` antes do primeiro `--testar-conexao`.
