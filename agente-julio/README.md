# Agente Julio — orquestrador conversacional

O Julio e a camada que fala com o humano (hoje: Telegram) e aciona os outros
agentes quando precisa executar algo. Ele nao sabe *como* cada agente
funciona por dentro — so chama o `main.py` deles como processo separado e
troca JSON pelo stdin/stdout. Isso mantem os agentes desacoplados: o
`agente-ads` pode mudar por completo por dentro que o Julio continua
funcionando, contanto que `--criar-campanha` continue aceitando o mesmo JSON.

Extraido do `agente-ads` (que antes tinha um `telegram_bot.py` fazendo
transporte + conversa + execucao tudo junto) em 2026-07-22 — ver
`../CLAUDE.md`.

## Arquitetura

```
telegram_transport.py   -> so fala com a API do Telegram (poll + envio)
orchestrator.py          -> conversa (LLM + tool-calling), decide quando propor
                             uma campanha e pede confirmacao humana
agentes.py                -> chama os outros agentes via subprocess
config.py                 -> .env.<SITE>, mesmo padrao dos outros modulos
```

Hoje o unico agente acionavel e o `agente-ads` (criar campanha nova). O
plano e crescer `agentes.py` com mais chamadas (rodar auditoria do
agente-gtm/ga4/search-console sob pedido, por exemplo) sem mexer no
`orchestrator.py`.

## Multi-site

Mesmo padrao dos outros: `SITE=<site> python main.py`. O briefing de
negocio (guardrails, ticket medio, margem) e lido direto de
`../agente-ads/CLAUDE.<SITE>.md` — nao duplicado aqui, pra nao haver risco
de um agente aprovar algo que o outro rejeitaria.

**Cuidado com o bot token do Telegram:** um mesmo bot so pode ter *um*
processo fazendo long polling por vez (`getUpdates` nao e multi-consumidor —
rodar 2 SITEs com o mesmo token ao mesmo tempo faz cada mensagem cair em um
processo aleatorio). Rode um SITE por vez, ou crie um bot novo no
`@BotFather` pra cada site que precisar rodar simultaneamente.

## Setup

1. `pip install -r requirements.txt`
2. Copie `.env.example` para `.env.<SITE>`. As chaves de LLM podem ser as
   mesmas do `../agente-ads/.env.<SITE>` (reaproveitar, nao duplicar
   sentido — sao credenciais diferentes, mas mesmo valor funciona).
3. Crie um bot com `@BotFather`, pegue o token, e o chat_id de quem vai usar
   (fale com `@userinfobot`). Preencha `TELEGRAM_BOT_TOKEN` e
   `TELEGRAM_AUTHORIZED_CHAT_IDS`.
4. `SITE=<site> python main.py`

## LLM_PROVIDER

Igual ao `agente-ads`: `LLM_PROVIDER=openai` ou `anthropic` no `.env.<SITE>`.
Se trocar no meio de uma conversa em andamento, o historico daquele chat e
descartado (formatos de tool-calling das duas APIs nao sao compativeis) —
o usuario so precisa repetir a ultima frase.

## Status

Criado em 2026-07-22, ainda nao testado com um bot real do Telegram (falta
gerar/confirmar o token com o usuario). Logica de LLM (`orchestrator.py`)
testada isoladamente contra o provider OpenAI configurado.
