# Agente GTM — Auditoria

Auditoria de saúde do container do Google Tag Manager. Sempre leitura — nunca
publica nem altera nada no GTM. Ver `../gtm-workflow.md` para o desenho
completo do workflow e `../brainstorm.md` (§2) para o contexto maior do
projeto.

Site coberto hoje: **Integra Foods** (laboratório — ver `../pratico.md`).

## Fluxo

```
gtm_auditor.py (Tag Manager API v2, read-only)
   -> compara versao live vs. workspace
   -> tags sem trigger, triggers orfaos
   -> confere a tag do GA4 contra o measurement ID esperado
```

## Setup

1. `pip install -r requirements.txt`
2. Copie `.env.example` para `.env`.
3. Confirme em https://tagmanager.google.com que a conta que vai autorizar
   tem acesso de leitura ao container (`accounts/6363669174/containers/257024578`
   — Integra Foods, `GTM-PJWJJHXR`).
4. Ative a **Tag Manager API** no projeto Cloud interno já usado pelo Ads
   (`agente-cmo-ads-interno` — ver
   `..\agente-cmo\docs\setup-do-zero-checklist.md`). Pode reaproveitar o
   mesmo `client_id`/`client_secret` desse projeto.
5. Gere o refresh token: `python generate_refresh_token_gtm.py` (copie a
   saída para o `.env`).

## Uso

| Comando | O que faz |
|---|---|
| `python main.py --auditar` | Roda a auditoria e imprime/salva o resultado em `data/` |

## Status

Código escrito, mas ainda não rodado — falta o passo 3-5 do setup (acesso ao
container confirmado + refresh token gerado). Ver `../pratico.md` (item 1)
para o checklist do que falta.
