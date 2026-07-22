# Agente Search Console — Auditoria

Auditoria de saúde orgânica/técnica do site no Google Search Console. Sempre
leitura — o Search Console não tem "ação executável" no sentido do GTM/Ads,
então este módulo só produz achados/alertas (ver `../brainstorm.md` §3.3).

Site coberto hoje: **Integra Foods** (laboratório — ver `../pratico.md`).

**Propriedade correta (confirmado 22/07/2026 navegando search.google.com):**
`https://integrafoods.ind.br/` (URL-prefix property), verificada,
`eduardo.rezende@integrafoods.ind.br` é Proprietário. Sitemap `/sitemap.xml`
enviado, processado, 404 páginas encontradas, sem erros.

Cuidado: existe também a propriedade do domínio antigo/staging
`https://if-ssr.conge.digital/` (de antes da migração de domínio em
16/07/2026) — não confundir, não mexer.

## Fluxo

```
search_console_auditor.py (Search Console API v1, read-only)
   -> status dos sitemaps (erros, avisos, paginas encontradas)
   -> desempenho de busca dos ultimos 28 dias (top queries, cliques,
      impressoes, posicao media)
   -> alerta se algum sitemap tem erro, ou se nao ha trafego organico
      registrado no periodo
```

Ver `referencia-api.md` (catálogo completo — só 11 métodos ao todo, a
menor das 4 APIs do projeto) pra candidatos a tool do `../agente-julio`,
em especial `urlInspection.index.inspect` (por que uma URL não indexa).

## Multi-site

`config.py` carrega `.env.<SITE>` (variável de ambiente `SITE`, ex:
`SITE=3gfoods python main.py --auditar`). Sem `SITE`, usa `integrafoods`.
Pra conectar um site novo, siga `../.claude/skills/onboard-site/SKILL.md`
em vez de repetir o setup manualmente.

## Setup (Integra Foods, `.env.integrafoods`)

1. `pip install -r requirements.txt`
2. Copie `.env.example` para `.env.integrafoods`.
3. ✅ Acesso já confirmado (22/07/2026) — `eduardo.rezende@integrafoods.ind.br`
   é Proprietário de `https://integrafoods.ind.br/`.
4. ✅ **Feito (22/07/2026)** — Search Console API ativada no projeto
   `agente-cmo-ads-interno`.
5. ✅ **Feito (22/07/2026)** — `SC_CLIENT_ID`/`SC_CLIENT_SECRET` reaproveitados
   do mesmo cliente OAuth dos outros agentes.
6. ✅ **Feito (22/07/2026)** — refresh token gerado com
   `generate_refresh_token_sc.py` e salvo no `.env.integrafoods`.

## Uso

| Comando | O que faz |
|---|---|
| `python main.py --auditar` | Roda a auditoria e imprime/salva o resultado em `data/` |

## Status

**Rodando.** Primeira auditoria real em 22/07/2026: sitemap `/sitemap.xml`
com 0 erros e 0 avisos (404 páginas); tráfego orgânico ativo nos últimos 28
dias, melhor query "integrafoods" (9 cliques, posição média 1.8).
