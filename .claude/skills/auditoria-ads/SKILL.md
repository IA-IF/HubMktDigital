---
name: auditoria-ads
description: >
  Roda a análise/recomendação (dry-run) da conta Google Ads de um site
  (Integra Foods, 3G Foods ou Adoro) — não executa nada, só lê e recomenda.
  Use quando o usuário pedir para auditar/checar a conta Ads, testar a
  conexão com uma conta, ou entender o estado atual de campanhas/lances
  antes de propor qualquer mudança. Não use para criar campanha ou
  executar ações aprovadas — isso é escrita e já tem fluxo próprio de
  confirmação (`propor_campanha` no agente conversacional).
---

# Auditoria/Dry-run Google Ads

Wrapper fino sobre `LEGADO/agente-ads/main.py`, que já existe e funciona.
Diferente dos outros 3 auditores, este módulo também sabe executar ações
(guardrail próprio, campanha sempre criada **pausada**) — esta skill cobre
só a parte de leitura/recomendação, não a de escrita.

## Pré-requisito: site explícito

Nunca infira o site. Slugs válidos: `integrafoods` (default se `SITE` não
for passado), `3gfoods`, `adoro`.

## Como rodar

```
cd LEGADO/agente-ads
SITE=<slug> python main.py --testar-conexao   # lista campanhas ativas, confere credenciais
SITE=<slug> python main.py --dry-run          # analisa e recomenda, sem executar nada (tambem e o default sem flag)
```

## Interpretando o resultado

Achados conhecidos a reconfirmar: contas Ads desconhecidas apareceram
linkadas a propriedades GA4 sem o usuário lembrar de tê-las criado (ex:
`7466004393` na 3G Foods) — se aparecer de novo, reporte, não decida
sozinho se é legítima. `propor_campanha` hoje não tem campo de geografia
granular (`GEO_TARGET_BRASIL` fixo) — isso é um achado de schema, não desta
skill.

## O que esta skill NÃO faz

- Não roda `--executar` nem `--criar-campanha` — criação/execução de
  campanha é sempre via `propor_campanha` no agente conversacional
  (schema + confirmação humana explícita antes de qualquer ação real).
- Não decide qual site auditar sozinha.
