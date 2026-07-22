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
orchestrator.py          -> conversa (LLM + tool-calling), pergunta o site,
                             decide quando propor uma campanha e pede
                             confirmacao humana
agentes.py                -> chama os outros agentes via subprocess
config.py                 -> .env unico (nao e multi-site — ver abaixo)
```

Hoje o unico agente acionavel e o `agente-ads` (criar campanha nova). O
plano e crescer `agentes.py` com mais chamadas (rodar auditoria do
agente-gtm/ga4/search-console sob pedido, por exemplo) sem mexer no
`orchestrator.py`.

## Por que o Julio NAO e multi-site como os outros agentes

`agente-ads`, `agente-gtm`, etc. resolvem o site por variavel de ambiente
(`SITE=3gfoods python main.py`) porque cada execucao deles e uma tarefa
pontual — faz sentido saber de antemao qual conta tratar.

O Julio e diferente: e um processo continuo escutando o Telegram, e um
unico bot atende aos 3 sites (Integra Foods, 3G Foods, Adoro) na mesma
conversa ao longo do tempo. Fixar o site num env var do processo faria o
Julio silenciosamente aplicar acoes no site errado se alguem esquecesse de
reiniciar o processo com o `SITE` certo — um erro caro (campanha criada na
conta errada). Por isso o site e uma pergunta obrigatoria dentro da propria
conversa (`orchestrator._perguntar_qual_site`, guardado em
`data/telegram_conversas/<chat_id>.json`), nunca um default silencioso.
Pra trocar de site no meio de uma conversa, mande `/site`.

O briefing de negocio (guardrails, ticket medio, margem) do site escolhido
e lido direto de `../agente-ads/CLAUDE.<site>.md` — nao duplicado aqui, pra
nao haver risco do Julio aprovar algo que o agente-ads rejeitaria.

## Setup

1. `pip install -r requirements.txt`
2. Copie `.env.example` para `.env`. As chaves de LLM podem ser as mesmas
   de qualquer `../agente-ads/.env.<site>` (sao credenciais de conta
   pessoal/projeto, nao por site).
3. Crie **um unico** bot com `@BotFather`, pegue o token, e o chat_id de
   quem vai usar (fale com `@userinfobot`). Preencha `TELEGRAM_BOT_TOKEN` e
   `TELEGRAM_AUTHORIZED_CHAT_IDS`.
4. `python main.py`

## LLM_PROVIDER

Igual ao `agente-ads`: `LLM_PROVIDER=openai` ou `anthropic` no `.env`. Se
trocar no meio de uma conversa em andamento, o historico daquele chat e
descartado (formatos de tool-calling das duas APIs nao sao compativeis) —
o usuario so precisa repetir a ultima frase.

## Status

Criado em 2026-07-22. Selecao de site e o loop de LLM (`orchestrator.py`)
testados isoladamente contra o provider OpenAI configurado — faz as
perguntas certas quando falta informacao, chama a tool `propor_campanha`
com o schema correto quando a proposta esta completa. Bot do Telegram em
si ainda nao testado com token real (falta rodar `main.py` de verdade).
