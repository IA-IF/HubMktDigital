---
name: auditoria-gtm
description: >
  Roda a auditoria de saúde do container Google Tag Manager de um site
  (Integra Foods, 3G Foods ou Adoro) — leitura via API (tags/triggers/
  variáveis sem trigger) e, opcionalmente, auditoria dinâmica com Playwright
  no site real (dataLayer, hits GA4 disparados de verdade). Use sempre que o
  usuário pedir para auditar, checar ou "ver o estado" do GTM de um site, ou
  quando outra tarefa (ex: investigar um bug de tracking) precisar saber
  quais tags/triggers/variáveis existem hoje num container. Não use para
  publicar ou editar o container — isso é escrita, fora de escopo desta
  skill (ver `agente-gtm/referencia-api.md`).
---

# Auditoria GTM

Wrapper fino sobre `LEGADO/agente-gtm/main.py`, que já existe e funciona —
esta skill só documenta quando/como chamá-lo, não reimplementa nada.

## Pré-requisito: site explícito

Nunca infira qual site auditar. Se o usuário não disse (ex: "audita o GTM"
sem nome de site), pergunte antes de rodar. Slugs válidos: `integrafoods`
(default se `SITE` não for passado), `3gfoods`, `adoro`.

## Como rodar

```
cd LEGADO/agente-gtm
SITE=<slug> python main.py --auditar             # config via API (tags, triggers, variáveis)
SITE=<slug> python main.py --auditar-dinamico     # Playwright no site real (dataLayer + hits GA4)
```

No Windows PowerShell: `$env:SITE="<slug>"; python main.py --auditar`.

`--auditar-dinamico` é mais lento (abre browser) mas pega problemas que a
auditoria estática não vê — ex: tag configurada mas que não dispara de
verdade, ou dataLayer com valor suspeito (já achou `quantity: 100` fixo e
falta de evento `view_item_list` na home da 3G Foods). Tem uma lição de
implementação registrada no código: esperar só `networkidle` do Playwright
dá falso negativo, é preciso espera extra depois disso.

## Interpretando o resultado

Leia a saída JSON/texto real, não assuma que "rodou sem erro" significa
"tudo certo" — confira contagem de tags, se triggers batem com tags, se
variáveis não usadas aparecem. Achados estruturais (container nunca
publicado, tag GA4 que não bate) são reportados ao usuário, não corrigidos
sozinho por esta skill.

## O que esta skill NÃO faz

- Não publica nem edita o container (`versions.publish` e afins) — é só
  leitura. Escrita em GTM tem guardrail próprio (workspace/rascunho,
  publish sempre manual) e é uma capacidade separada, ainda não construída
  nesta base.
- Não decide qual site auditar — sempre pede confirmação se não veio
  explícito na conversa.
