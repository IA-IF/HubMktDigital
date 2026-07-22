# Agente GA4 — Auditoria

Auditoria de saúde da propriedade do Google Analytics 4. Sempre leitura —
nunca altera configuração nem dados. Ver `../gtm-workflow.md` (mesmo padrão
de workflow) e `../brainstorm.md` (§2) para o contexto maior do projeto.

Site coberto hoje: **Integra Foods** (laboratório — ver `../pratico.md`).

**Conta/propriedade correta (confirmado 22/07/2026 navegando analytics.google.com):**
conta **"Integra Foods"** (`233412801`), propriedade **"IntegraFoods V2"**
(`543849199`), stream "SSR" → `https://integrafoods.ind.br`. Measurement ID
`G-CC4D18ST42` — bate com o que o GTM usa. Coleta de dados confirmada ativa
(tráfego, eventos de funil e compras aparecendo nos relatórios).

Cuidado: a mesma conta "Integra Foods" tem outras propriedades de outros
sites/clientes (3GFOODS, ADORO, CONGE, CONGEv2, Devito, Dinamica) — não
confundir a propriedade pelo nome da conta.

## Fluxo

```
ga4_auditor.py (Admin API + Data API v1beta, read-only)
   -> lista eventos marcados como conversao (Admin API)
   -> conta eventos do funil de ecommerce nos ultimos 7 dias (Data API)
   -> alerta se "purchase" nao esta marcado como conversao, ou se algum
      evento do funil esta zerado
```

## Multi-site

`config.py` carrega `.env.<SITE>` (variável de ambiente `SITE`, ex:
`SITE=3gfoods python main.py --auditar`). Sem `SITE`, usa `integrafoods`.
Pra conectar um site novo, siga `../.claude/skills/onboard-site/SKILL.md`
em vez de repetir o setup manualmente.

## Setup (Integra Foods, `.env.integrafoods`)

1. `pip install -r requirements.txt`
2. Copie `.env.example` para `.env.integrafoods`.
3. ✅ Acesso já confirmado (22/07/2026) — `eduardo.rezende@integrafoods.ind.br`
   tem papel "Administrador" na propriedade `543849199`.
4. ✅ **Feito (22/07/2026)** — Admin API e Data API ativadas no projeto
   `agente-cmo-ads-interno`.
5. ✅ **Feito (22/07/2026)** — `GA4_CLIENT_ID`/`GA4_CLIENT_SECRET` reaproveitados
   do mesmo cliente OAuth do `agente-gtm`.
6. ✅ **Feito (22/07/2026)** — refresh token gerado com
   `generate_refresh_token_ga4.py` e salvo no `.env.integrafoods`.

## Uso

| Comando | O que faz |
|---|---|
| `python main.py --auditar` | Roda a auditoria e imprime/salva o resultado em `data/` |

## Status

**Rodando.** Primeira auditoria real em 22/07/2026: `purchase` está marcado
como evento de conversão (junto com `close_convert_lead`, `qualify_lead`);
funil de ecommerce dos últimos 7 dias sem nenhum evento zerado (440
page_view → 66 view_item → 11 add_to_cart → 24 begin_checkout → 2 purchase).
