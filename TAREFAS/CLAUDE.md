# TAREFAS

Registro de configuração/comportamento do canal **telegram_v2** — o grupo
do Telegram onde Eduardo, Leandro e eu (Claude, rodando local no PC do
Eduardo) discutimos e decidimos tarefas. Existe pra não precisar
reanalizar o projeto do zero toda vez que essa conversa continuar numa
sessão nova.

## O que é o telegram_v2

- Bot: `t.me/iftelegramv2_bot` (nome de exibição `telegram_v2`).
- **Não passa pelo Julio nem pelo núcleo v2** (`ARQUITETURA/nucleo/`) —
  é um canal separado, sem agente/LLM próprio automático. Quem lê e
  decide a resposta sou eu, nesta sessão do Claude Code; o bot em si só
  transporta e loga mensagens.
- Roda **só localmente**, na máquina do Eduardo — não está no EC2.
- É um **grupo** do Telegram (não chats privados individuais) — bot com
  privacy mode desativado (`@BotFather` → `/mybots` → bot → `Bot
  Settings` → `Group Privacy` → `Turn off`), assim ele enxerga toda
  mensagem do grupo, não só `/comandos` ou menções.

## Quem são os 3

| Quem | Telegram user_id |
|---|---|
| Eduardo (dev) | `8297590261` |
| Leandro (gestor) | `8800634507` |
| Claude (eu) | aparece no log como `ia` |

Mapeamento em `BOTV2/config.py` (`NOMES_POR_USUARIO_ID`).

## Onde ficam os arquivos

- `BOTV2/canal.py` — cliente HTTP mínimo da Telegram Bot API
  (enviar/receber), sem dependência de `ARQUITETURA/`.
- `BOTV2/config.py` — token/allowlist (lidos de `REDIS/.env`:
  `TELEGRAM_V2_BOT_TOKEN`, `TELEGRAM_V2_AUTHORIZED_CHAT_IDS`), mapeamento
  de nomes, e o `chat_id` do grupo (capturado automaticamente, gravado em
  `BOTV2/logs/grupo_chat_id.txt`).
- `BOTV2/escutar.py` — loop de long-polling: grava cada mensagem
  autorizada (por `from.id`, já que no grupo o `chat_id` é o mesmo pra
  todo mundo) em `BOTV2/logs/conversa.md`. Não responde nada sozinho.
- `BOTV2/enviar.py` — como eu respondo no grupo: `python -m BOTV2.enviar
  "texto"`. Envia pro `chat_id` do grupo salvo e loga como `ia`.
- `BOTV2/logs/conversa.md` — histórico da conversa, formato
  `nome: mensagem`, uma entrada por linha (append-only, sem rotação por
  data).

## Como operar

1. Escutar precisa estar rodando em background:
   `python -m BOTV2.escutar` (raiz do projeto).
2. Pra responder: `python -m BOTV2.enviar "texto da resposta"`.
3. Pra saber o que rolou desde a última vez: ler
   `BOTV2/logs/conversa.md`.

## Decisões de design (por quê)

- **Grupo, não chat privado por pessoa**: Telegram já mostra as
  mensagens de todo mundo nativamente dentro de um grupo — não precisa
  de nenhuma lógica extra pra "juntar" as conversas dos dois.
- **Log em Markdown, não JSON**: pedido explícito do Eduardo — JSON traz
  problema de escaping de caractere, Markdown com `nome: msg` é
  suficiente e legível direto.
- **Sem agente/LLM automático no bot**: diferente do núcleo v2
  (`ARQUITETURA/nucleo/`), que tem loop próprio com Anthropic API e
  tools — aqui o "cérebro" sou eu, na sessão, não um processo autônomo
  rodando 24/7 decidindo sozinho.
