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
                             executa leituras na hora, pede confirmacao
                             humana so pra acoes com efeito real
agentes.py                -> chama os outros agentes via subprocess
pedidos.py                 -> registra em pedidos-futuros.md o que o Julio
                             ainda nao sabe fazer (nunca inventa resposta)
config.py                 -> .env unico (nao e multi-site — ver abaixo)
```

### As 3 ferramentas do LLM hoje

| Tool | Efeito | Confirmacao humana? |
|---|---|---|
| `consultar_trafego` | So leitura — chama `agente-ga4 --trafego` | Nao, executa na hora |
| `propor_campanha` | Cria campanha nova (PAUSADA) no `agente-ads` | **Sim** — para e pede sim/nao antes de acionar |
| `registrar_pedido_futuro` | Anota em `pedidos-futuros.md` | Nao (so escreve um arquivo) |

`registrar_pedido_futuro` existe pra cobrir qualquer pedido fora das outras
duas — o prompt tem uma regra inegociável contra inventar resposta ou
fingir ter executado algo (foi um problema real observado em teste: o LLM
quase confirmou "posso pausar essa keyword" sem ter nenhum tool pra isso,
confundindo os guardrails do `CLAUDE.<site>.md` — que descrevem o que o
pipeline automático `agente-ads` faz sozinho — com capacidades do próprio
Julio). `pedidos-futuros.md` é revisado manualmente, não vira implementação
sozinho.

O plano é crescer `agentes.py`/`orchestrator.py` com mais tools de leitura
conforme a lista de `pedidos-futuros.md` for sendo priorizada.

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

Criado em 2026-07-22. Testado ao vivo no Telegram (bot @IFMarketingAgentBot)
— achado e corrigido um bug real de rede (rota IPv6 ate api.telegram.org
degradada neste ambiente, ver `src/telegram_transport.py`). Loop de LLM
testado com os 3 providers/cenarios: `consultar_trafego` responde com dado
real sem interrogatorio, `propor_campanha` monta o schema certo e para pra
confirmacao, `registrar_pedido_futuro` recusa alucinar capacidade que nao
tem. Ainda nao testado: `propor_campanha` -> confirmacao -> criacao real de
campanha ponta a ponta (parou na simulacao/schema).
