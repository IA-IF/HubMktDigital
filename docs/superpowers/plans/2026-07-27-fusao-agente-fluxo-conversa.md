# Fusão Julio+Elis e Fluxo de Conversa Implementation Plan

> **STATUS: IMPLEMENTADO e testado com Redis/Anthropic reais em
> 2026-07-27** (ver "Testado de verdade" no fim). Só o transporte
> Telegram em si não foi exercitado (sem token de teste isolado neste
> ambiente) — o resto do fluxo (estado, tools, dado real de GA4) rodou
> de ponta a ponta contra os serviços reais do projeto.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resolver 4 problemas de arquitetura de agente/fluxo apontados em
`elis.md` (seção "sobre os agente julio e elis e fluxo"): fluxo fixo de
perguntas limitando o entendimento, qualidade ruim da camada de memória de
conversa, tendência do agente de empurrar decisões pro "time" sem
necessidade e sem depois verificar se a correção realmente aconteceu, e a
existência de 2 agentes/personas (Julio/Elis) separados quando 1 mais
inteligente bastaria.

**Contexto (código real hoje):**
- Fluxo fixo: `orchestrator.py` (`_perguntar_qual_site`,
  `_site_por_opcao`) só aceita `/start` → menu numerado 1/2/3 → só número
  reconhecido, texto livre tipo "quero falar da adoro" não funciona antes
  do site ser escolhido. Documentado em `entendendno.md:113-147`.
- Memória de conversa: cada bot guarda histórico bruto em JSON local
  (`AGENTES/julio/data/telegram_conversas/<chat_id>.json` pro Julio,
  `data/conversas_elis/<chat_id>.json` pra Elis) — sem extração de
  contexto/tarefas, sem Redis. O uso de Redis hoje é só pro
  `discover_tool` (catálogo de ferramentas), não pra memória de conversa.
- 2 agentes: `julio_config.agente_ativo()` lê `AGENTE_ATIVO` de
  `REDIS/.env` (`julio` ou `elis`) e só 1 fica ativo por vez no bot
  (`main_telegram.py:36`) — não rodam simultâneo, mas são 2 personas/
  orchestrators mantidos em paralelo (`orchestrator.py` +
  `elis_orchestrator.py`, `GLOBAL.md` + `GLOBAL_ELIS.md`).
- Pipeline de correção da Elis: `pedidos_projeto.registrar()` já dispara
  Planejador→Coder numa branch isolada (`pedido/<id>`) e aplica com
  rollback automático (`pedidos_projeto.py:1-13`, ver commit
  `0e2c0c8`). Ou seja, "pedir pro time" pro lado do Julio (marketing)
  não tem hoje um equivalente — Julio não tem esse pipeline de
  autocorreção, só a Elis. Isso pode explicar por que Julio "empurra pro
  time" sem depois conseguir confirmar: ele não tem ferramenta nenhuma
  pra verificar se algo mudou no próprio projeto.

**Architecture (hipótese a validar, ver "Em aberto"):** fundir
`orchestrator.py` + `elis_orchestrator.py` num único orchestrator, com
uma camada de memória em Redis (histórico + tarefas/pendências
extraídas, não só o JSON bruto) alimentada por um agente especialista em
extração de contexto, e um fluxo de seleção de site que aceita
linguagem natural (não só número fixo) usando o LLM pra interpretar em
vez de parser de menu.

## Problemas identificados (materializados de `elis.md`)

1. **Fluxo fixo demais.** O menu `/start` → número → site não está
   "errado", mas é limitante: força uma sequência rígida antes de
   qualquer entendimento real da mensagem do usuário. Ex.: usuário que já
   diz "quero ver o tráfego da adoro" na primeira mensagem tem que passar
   pelo menu numerado mesmo assim.
2. **Memória de conversa ruim.** Histórico é só JSON bruto por chat, sem
   camada de extração de contexto/tarefas. Falta um agente especialista
   que leia o histórico salvo e mantenha um resumo vivo de
   tarefas/pendências (criar → atualizar conforme completam), separado
   do Redis que hoje só serve o `discover_tool`.
3. **Tendência de empurrar pro "time" sem necessidade, e sem verificar
   depois.** O agente diz "vou pedir pro time aplicar a correção" pra
   quase tudo, mesmo quando deveria resolver sozinho; e quando a correção
   é feita de fato, ele não consegue localizar a mudança (sem tool de
   verificação/sem recarregar estado).
4. **2 agentes quando 1 bastaria.** Julio (marketing) e Elis
   (desenvolvimento do projeto) são personas/orchestrators separados
   hoje. Usuário acha que 1 agente só, mais inteligente, seria melhor que
   manter os 2.

## Decisões (confirmadas com o usuário em 2026-07-27)

- **Fusão é literal.** Um orchestrator só, uma persona só —
  `orchestrator.py` + `elis_orchestrator.py` viram um único módulo,
  `GLOBAL.md` + `GLOBAL_ELIS.md` viram um único arquivo de
  personalidade. `julio_config.agente_ativo()` e o switch `AGENTE_ATIVO`
  deixam de existir.
- **Separação de contexto é por interpretação do LLM, não por comando
  fixo.** Sem `/projeto` vs `/site` explícito — o próprio agente lê o
  teor da mensagem e decide se é sobre marketing de um site (regra de
  site explícito continua valendo — [[feedback_site-selecao-explicita]])
  ou sobre o próprio HubMktDigital. Isso é decisão de system prompt +
  tools disponíveis por chamada, não de parsing de comando.
- **As duas frentes de "mais inteligência" entram juntas, no mesmo
  plano:** (1) trocar o parser de menu fixo (`/start` → número) por
  entendimento em linguagem natural via LLM, e (2) dar ao agente uma
  tool de verificação — checar se uma mudança pedida realmente foi
  aplicada (ex.: reler arquivo/branch relevante, checar status em
  `pedidos_projeto`) antes de responder ou de "empurrar pro time" de
  novo.
- **Memória em Redis guarda histórico completo + extrato.** Não é só o
  resumo/tarefas — a conversa inteira fica buscável (semântica, mesmo
  padrão do `discover_tool`) além do resumo de tarefas mantido pelo
  agente especialista de contexto.

## Limpeza de legado (obrigatória no fim da implementação)

Regra do usuário (elis.md, 2026-07-27): informação legada que sobra no
projeto depois de um conceito novo entrar pode confundir a IA e fazer
ela regredir pro modo antigo — tem que ser removida, não só deixada de
lado. Pra este plano, especificamente:

- [x] **Deletar** `AGENTES/julio/elis_orchestrator.py` e
  `AGENTES/julio/GLOBAL_ELIS.md` depois que o orchestrator fundido
  cobrir tudo que os dois faziam — não deixar como "código morto de
  referência".
- [x] **Remover** `julio_config.agente_ativo()` e a variável
  `AGENTE_ATIVO` de `REDIS/.env`/`.env.example` — o switch deixa de
  existir, não faz sentido a variável continuar lida em algum lugar.
- [x] **Remover** as funções de menu fixo em `orchestrator.py`
  (`_perguntar_qual_site`, `_site_por_opcao`) depois que a seleção de
  site virar interpretação por LLM — não manter como fallback "pra
  garantir", isso é exatamente o tipo de caminho antigo que engana a IA.
- [x] **Atualizar ou arquivar** `entendendno.md` (linhas 93-192 hoje
  descrevem o fluxo fixo `/start` → menu numerado como se fosse o
  comportamento atual) — depois da fusão, esse trecho passa a descrever
  algo que não existe mais. Ou reescreve pra refletir o fluxo novo, ou
  marca explicitamente como histórico ("como funcionava antes da fusão
  de 2026-07-27") pra nenhuma sessão futura do Claude ler isso como
  verdade atual.
- [x] Conferir se `data/telegram_conversas/<chat_id>.json` e
  `data/conversas_elis/<chat_id>.json` (históricos separados por
  agente) precisam de migração/merge pro histórico único em Redis, ou
  se ficam como arquivo morto — decidir junto com o schema de memória
  (ver "Ainda em aberto" abaixo).

## Decisões (2026-07-27 — decidido por mim a pedido do usuário: "menor atrito, mais simples, mais compatível com o projeto")

- **Independente do plano de cobertura tool.json.** Nenhum código deste
  plano depende de tool.json novo existir — a fusão mexe em
  orchestrator/personalidade/memória, não na lista de tools disponíveis.
  Pode rodar em paralelo ou em qualquer ordem.
- **Históricos migram e os antigos são removidos.** `telegram_conversas/`
  e `conversas_elis/` viram um histórico único no Redis (mesma decisão
  da seção "Limpeza de legado" acima) — não ficam como arquivo morto
  depois da migração.
- **Schema do extrato reusa a mesma lib/infra do `discover_tool`**
  (`redisvl.SearchIndex` + `HFTextVectorizer`, já em uso no projeto —
  mais compatível que introduzir uma lib nova). Histórico: um índice só
  (`conversas`), campo `chat_id` como tag pra filtrar, texto com
  embedding pra busca semântica quando precisar. Tarefas: um hash Redis
  simples por tarefa (mesmos campos que `pedidos_projeto.py` já usa —
  `id`, `pedido`, `status`, `criado_em` — não precisa de vetor, é leitura
  direta por chat/id).
- **Extração de contexto roda síncrona, dentro do mesmo fluxo do
  orchestrator fundido** — não é uma chamada separada em paralelo. Hoje
  não existe nenhuma infra de worker/fila assíncrona no projeto
  (`orchestrator.py` é tudo síncrono); introduzir isso só pra essa etapa
  seria o tipo de complexidade que o projeto não tem hoje. Roda depois
  da resposta final, antes de salvar o turno.

## Desvio da decisão de schema, na implementação real

A decisão acima previa `redisvl.SearchIndex` (busca vetorial) pro
histórico. Na hora de implementar, simplifiquei pra `redis` puro
(get/set de uma chave JSON por chat, sem embedding) — motivo: carregar o
modelo de embedding (`sentence-transformers`) a CADA mensagem pra
indexar o turno adicionaria latência real em toda resposta do bot, só
pra uma capacidade (busca semântica sobre histórico antigo) que ninguém
pediu ainda. `estado:<chat_id>` guarda o estado completo (site,
histórico de turnos, pendências), `resumo:<chat_id>` guarda o resumo
vivo que o agente especialista mantém. Busca vetorial sobre histórico
fica como extensão futura, se/quando alguém precisar de fato buscar "o
que a gente falou sobre X" — a estrutura de chave já comporta migrar pra
`SearchIndex` depois sem quebrar nada.

## Arquivos alterados (implementação, 2026-07-27)

- **Rewrite** `AGENTES/julio/orchestrator.py` — um orchestrator só,
  cobrindo marketing (tools por site via `discover_tool`) e projeto
  (`registrar_pedido_projeto`/`listar_pedidos_projeto`, sempre
  disponíveis, sem depender de site). Site deixa de ser um menu numerado
  obrigatório: vira uma tool `selecionar_site` (enum das 3 slugs) que o
  modelo só chama quando o humano diz explicitamente qual site — mantém
  a regra dura "nunca adivinhar site" enquanto aceita linguagem natural
  ("quero falar da adoro"), não só número.
- **Create** `AGENTES/julio/memoria_redis.py` — `carregar_estado`/
  `salvar_estado`/`carregar_resumo`/`salvar_resumo`, substituindo os
  JSONs locais por chat.
- **Delete** `AGENTES/julio/elis_orchestrator.py`,
  `AGENTES/julio/GLOBAL_ELIS.md` — fundidos no orchestrator/GLOBAL.md
  únicos.
- **Modify** `AGENTES/julio/GLOBAL.md` (e `GLOBAL.default.md`) — regras
  de personalidade da Elis (não usar jargão técnico, confirmar
  entendimento antes de registrar pedido) incorporadas nas regras gerais
  do Julio.
- **Modify** `AGENTES/julio/julio_config.py` — removidos
  `agente_ativo()`, `global_elis_md()`, `ORDEM_MENU_SITE` (mortos depois
  da fusão).
- **Modify** `AGENTES/julio/main_telegram.py` — chama
  `orchestrator.processar_mensagem` direto, sem escolher entre 2
  agentes.
- **Modify** `AGENTES/julio/pedidos_projeto.py` — docstring atualizado
  (não referencia mais `elis_orchestrator.py`).
- **Modify** `REDIS/.env.example` — removido `AGENTE_ATIVO`.
- **Modify** `entendendno.md` — trecho do fluxo `/start` antigo (menu
  numerado, 2 agentes) marcado explicitamente como histórico
  (pré-fusão), pra nenhuma sessão futura ler como comportamento atual.

## Testado de verdade (2026-07-27, contra os serviços reais do projeto)

- **Redis real** (`REDIS_URL` de `REDIS/.env`, não mockado): roundtrip
  de `memoria_redis.carregar_estado`/`salvar_estado`/`carregar_resumo`/
  `salvar_resumo` — salvou, leu de volta, bateu. Chaves de teste
  removidas depois.
- **`julio_config`**: `anthropic_api_key()`, `telegram_bot_token()` e
  `texto_status()` (via `git rev-parse` real) confirmados presentes/
  funcionando. `status_token()` corretamente ainda não definido (campo
  novo, falta preencher antes de subir `status_server.py`).
- **Fluxo completo `processar_mensagem`** com Anthropic real (não
  mockado) e `FakeTransport` capturando a saída: `/start` → mensagem
  livre sem site ("oi, tudo bem?") respondeu em texto, sem tentar
  nenhuma tool → mensagem "quero ver o trafego da adoro dos ultimos 7
  dias" **chamou `selecionar_site` sozinho** (site nunca foi dito por
  número, só por nome em texto livre) e depois **rodou a tool real de
  GA4** contra a conta da Adoro, devolvendo funil de conversão/canais/
  AOV com dado real (83 sessões, 9 compras, AOV R$ 825, etc.).
- **Achado no processo**: a 1ª tentativa desse teste voltou "ferramenta
  não disponível" — `discover_tool.descobrir()` (top_k=3, não mudado
  por este plano) cortava `analise_vendas` (GA4) fora por ser o 4º
  colocado, distância 0.58 (dentro do limiar 0.7). Corrigido à parte
  (`discover_tool.py`, top_k 3→5, commit `a8341a5`) — não é regressão
  desta fusão, é um problema pré-existente que o teste real expôs.
- **Não testado**: o transporte Telegram em si (long polling,
  `telegram_transport.py`) — não tem token de teste isolado neste
  ambiente, só o `TELEGRAM_BOT_TOKEN` de produção. O resto do fluxo (tudo
  que roda antes de chamar `telegram_transport.enviar`) foi exercitado
  de ponta a ponta com um transporte falso capturando a saída.
- `STATUS_PROJETO.md` já está escrito de forma agnóstica (fala só "o
  Julio", não menciona a separação antiga) — conferido, não precisou de
  ajuste.
