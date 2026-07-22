# Agente GTM — Auditoria

Auditoria de saúde do container do Google Tag Manager. Sempre leitura — nunca
publica nem altera nada no GTM. Ver `../gtm-workflow.md` para o desenho
completo do workflow e `../brainstorm.md` (§2) para o contexto maior do
projeto.

Site coberto hoje: **Integra Foods** (laboratório — ver `../pratico.md`).

**⚠️ Existem 2 containers GTM ligados ao Integra Foods na conta Google — não confundir:**
o correto/ativo é a conta **"IF V2"**, container `GTM-PJWJJHXR` (`ifv2.conge.digital`), que é o
que este projeto usa. A conta **"Integra Foods"**, container `GTM-W6GWZX5`
(`www.integrafoods.ind.br`), é **LEGADO** — ignorar, não auditar, não mexer.

## Fluxo

```
gtm_auditor.py (Tag Manager API v2, read-only)
   -> compara versao live vs. workspace
   -> tags sem trigger, triggers orfaos
   -> confere a tag do GA4 contra o measurement ID esperado
```

## Multi-site

`config.py` carrega `.env.<SITE>` (variável de ambiente `SITE`, ex:
`SITE=3gfoods python main.py --auditar`). Sem `SITE`, usa `integrafoods`.
Pra conectar um site novo, siga `../.claude/skills/onboard-site/SKILL.md`
em vez de repetir o setup manualmente.

## Setup (Integra Foods, `.env.integrafoods`)

1. `pip install -r requirements.txt`
2. Copie `.env.example` para `.env.integrafoods`.
3. ✅ **Feito (22/07/2026)** — confirmado em tagmanager.google.com que
   `eduardo.rezende@integrafoods.ind.br` já tem acesso nível "Publicação" ao
   container `GTM-PJWJJHXR` (conta IF V2, `accounts/6363669174/containers/257024578`).
   Cobre com folga o scope `tagmanager.readonly` que este projeto usa.
4. ✅ **Feito (22/07/2026)** — Tag Manager API ativada no projeto
   `agente-cmo-ads-interno` (mesmo `client_id`/`client_secret` do Ads).
5. ✅ **Feito (22/07/2026)** — refresh token gerado com
   `generate_refresh_token_gtm.py` e salvo no `.env.integrafoods`.

## Uso

| Comando | O que faz |
|---|---|
| `python main.py --auditar` | Roda a auditoria e imprime/salva o resultado em `data/` |

## Status

**Rodando.** Primeira auditoria real em 22/07/2026: container saudável — 2
tags, 1 trigger, 5 variáveis, tudo publicado (0 mudanças pendentes), 0 tags
sem trigger, 0 triggers órfãos, tag GA4 confere com `G-CC4D18ST42`.

Próximos passos (fora do escopo desta auditoria estática): confirmar que a
tag GA4 dispara de verdade em produção e que a tag de e-commerce cobre todo
o funil (view_item, add_to_cart, purchase) — ver decisão em aberto no
`../gtm-workflow.md` sobre auditoria dinâmica (navegar o site de verdade).
