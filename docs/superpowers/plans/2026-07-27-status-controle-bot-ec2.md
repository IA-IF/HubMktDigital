# Controle e Status do Bot na EC2 Implementation Plan

> **STATUS: RASCUNHO — requisitos ainda em levantamento com o usuário
> (ver `elis.md`), não pronto pra virar tasks executáveis.**

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
