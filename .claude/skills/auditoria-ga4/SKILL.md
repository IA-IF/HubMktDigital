---
name: auditoria-ga4
description: >
  Roda a auditoria de saúde da propriedade GA4 (conversões, funil de
  ecommerce) ou um resumo de tráfego por canal de um site (Integra Foods,
  3G Foods ou Adoro). Use quando o usuário pedir para auditar/checar o GA4,
  perguntar sobre tráfego, sessões, conversões ou vendas recentes de um
  site, ou quando outra tarefa precisar de dado real de GA4 (ex: definir
  orçamento de campanha com base em receita média). Não use para editar
  eventos de conversão, custom dimensions ou links do Google Ads na
  propriedade — isso é escrita, fora de escopo desta skill.
---

# Auditoria/Tráfego GA4

Wrapper fino sobre `LEGADO/agente-ga4/main.py`, que já existe e é usado ao
vivo (inclusive chamado pelo `agente-julio`/`agente-conversacional` para
responder perguntas de tráfego no Telegram).

## Pré-requisito: site explícito

Nunca infira o site. Slugs válidos: `integrafoods` (default se `SITE` não
for passado), `3gfoods`, `adoro`.

## Como rodar

```
cd LEGADO/agente-ga4
SITE=<slug> python main.py --auditar               # saude da propriedade: conversoes, funil
SITE=<slug> python main.py --trafego --dias 7       # resumo de trafego + ecommerce por canal
```

`--dias` aceita qualquer inteiro (default 7) — use um período maior se o
pedido for sobre tendência, não só "como foi essa semana".

## Interpretando o resultado

Já existem achados conhecidos que valem checar de novo em cada rodada: 3G
Foods teve 9 eventos não-comerciais marcados como conversão (diluindo smart
bidding) e um "Adicionar ao carrinho" que na verdade contava
`remove_from_cart` — ver `pratico.md`. Não assuma que esses já foram
corrigidos; confirme no resultado da auditoria atual.

## O que esta skill NÃO faz

- Não edita `conversionEvents`, `customDimensions` nem `googleAdsLinks` —
  é só leitura. Escrita na GA4 Admin API é uma capacidade separada, com
  guardrail de confirmação humana antes de qualquer mudança.
- Não decide qual site auditar sozinha.
