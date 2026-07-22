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

dataLayer_auditor.py (Playwright headless, abre o site DE VERDADE)
   -> le window.dataLayer real da pagina
   -> confere que o container GTM esperado carregou (nao qualquer GTM)
   -> confere que o hit do GA4 realmente saiu com o measurement ID esperado
   -> flags: dataLayer vazio, quantidade fixa suspeita nos itens de ecommerce
```

Os dois são complementares: `--auditar` confirma que a *configuração* está
certa; `--auditar-dinamico` confirma que o *comportamento em produção*
bate com essa configuração (um site pode passar na auditoria estática e
mesmo assim não disparar nada de verdade). Ver `../brainstorm.md` §2.1
para a decisão de arquitetura por trás disso.

Ver `referencia-api.md` (catálogo completo da API, extraído do discovery
document ao vivo — ~50 métodos, maioria escrita) pra contexto de quais
métodos de leitura ainda não usamos e valeriam virar tool do `../agente-julio`.

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
| `python main.py --auditar` | Auditoria estática (config do container via API) |
| `python main.py --auditar-dinamico` | Abre o `SITE_URL` de verdade e confere dataLayer + hits reais (precisa `pip install playwright && playwright install chromium`) |

## Status

**Rodando (estático + dinâmico, 22/07/2026).** Estático: container
saudável — 2 tags, 1 trigger, 5 variáveis, tudo publicado, tag GA4 confere
com `G-CC4D18ST42`. Dinâmico, rodado nos 3 sites:

| Site | Container/measurement carregou | Achado |
|---|---|---|
| Integra Foods | ✅ | `quantity: 100` fixo em 100% dos itens de `view_item_list` (4 vitrines, 48 itens) — parece placeholder |
| 3G Foods | ✅ (precisou de espera extra, ver nota abaixo) | **Home não dispara nenhum `view_item_list`** — diferente dos outros 2 sites, vale confirmar se é intencional |
| Adoro | ✅ | Mesmo padrão de `quantity` fixo suspeito do Integra Foods |

Nota de implementação: `wait_until="networkidle"` sozinho deu falso
negativo pro 3G Foods (site com mais scripts de terceiros — Merchant
Center, várias tags de Ads — GTM carrega alguns segundos depois do idle).
`dataLayer_auditor.py` já inclui uma espera extra de 8s pra evitar isso.
