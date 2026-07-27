# Controle e Status do Bot na EC2 Implementation Plan

> **STATUS: IMPLEMENTADO, DEPLOYADO E TESTADO EM PRODUÇÃO em 2026-07-27**
> — ver "Testado de verdade em produção" no fim. Nada pendente.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dar ao gestor (não-técnico, sem acesso SSH) uma forma de
iniciar, parar e verificar se o bot do Telegram está ativo na EC2, sem
depender de alguém entrar via SSH pra rodar `pkill`/`nohup` manualmente
quando o bot cai. Além disso, expor a versão do bot e de onde ele está
rodando (EC2 vs máquina local de desenvolvimento), pra nunca ficar
ambíguo qual instância está respondendo no Telegram.

**Contexto (código real hoje):**
- O bot sobe/derruba hoje via `reiniciar_bot.py` (mata com `pkill -f
  main_telegram.py`, sobe com `nohup`/`setsid`, ver
  `AGENTES/julio/reiniciar_bot.py:24-35`) — mas isso só roda automatico,
  disparado por `pedidos_projeto.aplicar()` depois de um merge. Não tem
  hoje nenhum jeito do gestor (sem SSH) disparar isso manualmente quando
  o bot trava por outro motivo (erro de API, credencial expirada, etc).
- Existem 2 scripts `.ps1` na raiz (`iniciar-bot.ps1`, `parar-bot.ps1`)
  mas são **locais** (Windows, máquina de dev) — não ajudam com a EC2.
- `infra/ec2/README.md` hoje é só a linha de SSH — não tem processo de
  deploy documentado além de `infra/ec2/deploy.ps1` /
  `infra/ec2/puxar-mudancas.ps1` (rodados da máquina local).
- Não existe hoje nenhuma versão/build id exposta em lugar nenhum — sem
  jeito de saber, olhando o Telegram, se quem está respondendo é a EC2
  de produção ou alguém testando local.

## Decisões (confirmadas com o usuário em 2026-07-27)

- **Proteção do endpoint: token compartilhado.** Uma página/endpoint
  HTTP na EC2 com start/stop/status, protegida por um token fixo (tipo
  senha longa) no header ou querystring — não é login usuário/senha, não
  é IP allowlist. O token vai em `.env` (gitignored, nunca no
  repositório) e é passado pro gestor fora do código (ex.: mensagem
  direta, não commitado).
- **Versão/origem aparece via comando no Telegram.** Um comando tipo
  `/status` no próprio bot responde a versão (ex.: hash curto do commit
  atual) e de onde está rodando (`EC2` vs `local`) — não fica só na
  página HTTP, fica acessível de dentro da conversa que o gestor já usa.

## Decisões (2026-07-27 — decidido por mim a pedido do usuário: "menor atrito, mais simples, mais compatível com o projeto")

- **Endpoint roda como processo separado**, não embutido no
  `main_telegram.py`. Não é escolha de simplicidade pura — é a única que
  funciona pro objetivo real: se o endpoint vivesse dentro do processo
  do bot, ele morreria junto quando o bot travasse, que é exatamente o
  cenário que o gestor precisa conseguir contornar. Reusa o padrão que
  `reiniciar_bot.py` já estabeleceu (`pkill`/`pgrep`/`nohup` — mesma
  técnica, nada novo pro projeto).
- **Hash de versão: `git rev-parse --short HEAD` rodado na hora**, sem
  gravar nada no deploy. Mais simples (zero mudança em
  `infra/ec2/deploy.ps1`) e compatível com o padrão do projeto de nunca
  guardar estado derivável quando dá pra calcular na hora.
- **Token no `REDIS/.env`** — mesmo arquivo que já centraliza
  `AGENTE_ATIVO` e credenciais Redis; não vale criar um segundo lugar de
  segredo só pra isso.
- **HTTP por enquanto, sem HTTPS.** Uso interno, baixo tráfego, e
  nenhuma outra parte do projeto tem HTTPS hoje — adicionar
  nginx+certbot seria atrito desproporcional ao risco atual. Mitigação
  mínima: token vai em **header**, não em querystring (querystring cai
  em log de acesso; header não).
- **Independente dos outros 3 planos** — confirmado, nenhuma dependência
  de código entre eles.

## Arquivos alterados (implementação, 2026-07-27)

- **Create** `AGENTES/julio/bot_processo.py` — `matar_bot()`,
  `subir_bot()`, `bot_vivo()` extraídos de `reiniciar_bot.py` (mesmo
  comportamento, agora reusável por `status_server.py` também).
- **Modify** `AGENTES/julio/reiniciar_bot.py` — usa
  `bot_processo.{matar_bot,subir_bot,bot_vivo}` em vez de funções
  locais duplicadas.
- **Create** `AGENTES/julio/status_server.py` — servidor HTTP stdlib
  (`http.server`, zero dependência nova), processo separado do bot:
  `GET /status` (bot_vivo + ambiente), `POST /iniciar`, `POST /parar`,
  todos exigindo header `X-Status-Token` igual a `config.status_token()`.
- **Modify** `AGENTES/julio/julio_config.py` — `status_token()`,
  `status_server_port()` (default 8765), `ambiente()` (`AMBIENTE` do
  `.env`, default `"local"`), `texto_status()` (hash curto do commit via
  `git rev-parse` + ambiente).
- **Modify** `AGENTES/julio/orchestrator.py` (comando único depois da
  fusão Julio+Elis — `elis_orchestrator.py` não existe mais) — comando
  `/status` via `config.texto_status()`, respondido direto no Telegram.
- **Modify** `REDIS/.env.example` — `AMBIENTE`, `STATUS_TOKEN`,
  `STATUS_SERVER_PORT` documentados.
- **Modify** `infra/ec2/README.md` — como subir o `status_server.py` na
  EC2 (`nohup`) e exemplos de `curl` pros 3 endpoints.

## Testado de verdade em produção (2026-07-27)

- `git push` + deploy real na EC2 (`infra/ec2/deploy.ps1`) — bot que
  estava **parado** (confirmado por SSH antes de mexer) subiu com o
  código novo, confirmado depois via Redis (estado real gravado pro
  chat_id do usuário testando no Telegram de verdade).
- `STATUS_TOKEN` real gerado (`secrets.token_urlsafe(32)`) e gravado só
  no `REDIS/.env` da EC2 (nunca commitado) via SSH.
- `status_server.py` subido na EC2 (processo separado, PID confirmado
  vivo por `ps aux`).
- **Security group da EC2 não tinha a porta 8765 aberta** — achado no
  processo, corrigido com confirmação explícita do usuário
  (`aws ec2 authorize-security-group-ingress`, porta 8765, mesma faixa
  0.0.0.0/0 das outras portas públicas do projeto — decisão de proteger
  por token, não por IP, já tomada antes).
- **Os 3 endpoints testados via `curl` reais contra a EC2 pública**:
  `GET /status` sem token → `401`; com token → `{"bot_vivo": true,
  "ambiente": "EC2"}`; `POST /parar` → bot morreu de verdade
  (`bot_vivo: false` confirmado); `POST /iniciar` → bot voltou
  (`bot_vivo: true` confirmado) — ciclo completo de recuperação sem SSH
  validado ponta a ponta.
