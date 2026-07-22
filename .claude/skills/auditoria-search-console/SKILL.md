---
name: auditoria-search-console
description: >
  Roda a auditoria de saúde do Google Search Console de um site (Integra
  Foods, 3G Foods ou Adoro) — sitemaps enviados, erros de indexação,
  cobertura. Use quando o usuário pedir para auditar/checar SEO, indexação
  ou o Search Console de um site, ou quando outra tarefa precisar saber se
  um sitemap foi enviado ou se há páginas com erro de indexação. Não use
  para enviar sitemap ou pedir inspeção de URL de escrita — isso é ação,
  fora de escopo desta skill (hoje só leitura).
---

# Auditoria Search Console

Wrapper fino sobre `LEGADO/agente-search-console/main.py`, que já existe e
funciona.

## Pré-requisito: site explícito

Nunca infira o site. Slugs válidos: `integrafoods` (default se `SITE` não
for passado), `3gfoods`, `adoro`.

## Como rodar

```
cd LEGADO/agente-search-console
SITE=<slug> python main.py --auditar
```

## Interpretando o resultado

Achado conhecido: a Adoro apareceu com 0 sitemaps enviados numa auditoria
anterior — confirme se isso ainda é verdade em vez de assumir que já foi
corrigido.

## O que esta skill NÃO faz

- Não chama `sitemaps.submit` nem `urlInspection.index.inspect` — essas
  chamadas de escrita/inspeção ativa estão mapeadas em
  `agente-search-console/referencia-api.md` mas não implementadas ainda.
  Quando existirem, serão uma tool separada com confirmação humana antes de
  executar.
- Não decide qual site auditar sozinha.
