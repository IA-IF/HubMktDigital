# Pesquisa de Técnicas de Campanha + Perfil de Cliente (Redis) Implementation Plan

> **STATUS: IMPLEMENTADO e testado de ponta a ponta com Redis/Anthropic/
> web search reais em 2026-07-27** — ver "Testado de verdade" no fim.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Duas capacidades novas, relacionadas: (1) pesquisar técnicas de
campanha de alta conversão pra Google Ads, comparar com o estado real da
conta (públicos, segmentação, conversões configuradas ou não) e gerar
tarefas concretas pra fechar o gap; (2) mover o perfil de cliente (quem é,
o que vende, pra quem vende) pra Redis, substituindo o `RULES.md` por
site que hoje está vazio.

**Contexto (código real hoje):**
- `SITES/{3gfoods,adoro,integrafoods}/RULES.md` são só o template
  (`Publico-alvo:`, `Orcamento diario tipico:`, `ROAS-alvo:`,
  `Produtos/linhas em foco:`) — **nenhum dos 3 foi preenchido**, todos
  terminam em "TODO: preencher.". Isso confirma o ponto da Elis: hoje
  não existe, em lugar nenhum, uma análise real de quem é o cliente.
- Já existe 1 exemplo do padrão "pesquisar técnica → comparar com o que
  existe → virar spec/tarefa": `docs/superpowers/specs/2026-07-24-skag-ads-negative-keywords-design.md`,
  construído a partir da transcrição de um vídeo (`video.md`/
  `analise_video.md`), comparando a técnica (SKAG, negative keywords)
  contra o que `TOOLS/ADWORDS/criar_campanha` já faz hoje, e definindo o
  que muda. Isso foi feito manualmente por mim (Claude) nesta sessão —
  não existe como capacidade repetível/tool do agente.
- Ações que mudam a CONTA do Google Ads/GA4 (criar público, segmentação,
  evento de conversão) já têm um princípio de fluxo de confirmação
  citado no `CLAUDE.md` da skill `auditoria-ads`: "isso é escrita e já
  tem fluxo próprio de confirmação (`propor_campanha` no agente
  conversacional)". `TOOLS/ADWORDS/criar_campanha` (validação +
  construtor) é o único exemplo de tool de escrita implementada hoje.

## Decisões (confirmadas com o usuário em 2026-07-27)

- **Perfil de cliente substitui `RULES.md`.** Os 3 `RULES.md` (hoje
  vazios) saem de uso — público-alvo, orçamento, ROAS-alvo, produtos em
  foco passam a viver em Redis, junto com o resto do perfil (quem é o
  cliente, o que vende, pra quem vende). Fica mais simples criar/
  atualizar do que editar markdown manualmente.
- **Tarefas de conta (público/segmentação/conversão) reusam o fluxo de
  escrita já existente**, no mesmo padrão de `propor_campanha` — não o
  pipeline de código da Elis (`pedidos_projeto`, que é
  branch/merge/rollback git, não faz sentido pra uma mudança dentro da
  conta Google Ads/GA4). Decisão tomada por mim (Claude), a pedido do
  usuário ("decide o melhor pra o projeto") — motivo: `pedidos_projeto`
  manipula o repositório git do próprio HubMktDigital; ações de conta
  Google não tocam código nenhum, então usar o mesmo pipeline colocaria
  um merge/rollback de branch em cima de algo que não é arquivo nenhum.
- **Pesquisa de técnica é sob demanda**, não periódica/proativa — só
  roda quando alguém pede ("pesquisa técnicas novas pra X").

## Duas frentes deste plano

### Frente 1: Perfil de cliente em Redis

Schema mínimo por site (a definir no File Structure da fase de
implementação): público-alvo, orçamento diário típico, ROAS-alvo,
produtos/linhas em foco — os mesmos 4 campos do template atual do
`RULES.md`, mais o que a Elis pediu explicitamente e não está no
template hoje: **quem é o cliente, o que ele vende, pra quem ele vende**
(isso é mais amplo que "produtos/linhas em foco" — é o contexto de
negócio, não só o catálogo).

### Frente 2: Pesquisa de técnica de campanha

Fluxo: (1) pesquisa na internet sobre técnica de alta conversão pro
domínio pedido, (2) compara contra o estado real da conta (útil ter
`consultar_trafego`/tools de auditoria já existentes — `auditoria-ads`,
`auditoria-ga4` — pra saber o que já está configurado), (3) gera tarefas
concretas. A maior parte das verificações técnicas se resume a checar se
os serviços do Google (públicos, segmentação, conversões, etc.) já
existem configurados ou não.

## Limpeza de legado (obrigatória no fim da implementação)

Regra do usuário (elis.md, 2026-07-27): informação legada que sobra
depois de um conceito novo entrar pode confundir a IA e fazer ela
regredir pro modo antigo — tem que ser removida, não só deixada de lado.
Pra este plano, especificamente:

- [x] **Deletar o conteúdo dos 3 `RULES.md`** (`SITES/3gfoods/RULES.md`,
  `SITES/adoro/RULES.md`, `SITES/integrafoods/RULES.md`) depois que o
  perfil de cliente estiver de fato em Redis e sendo lido de lá — não
  deixar o arquivo vazio "TODO: preencher" no repo, porque se algum
  código ou algum Claude futuro ainda ler esse arquivo (por hábito, por
  busca de contexto), ele vai achar que não há perfil nenhum, mesmo com
  o dado real já em Redis.
- [x] **Atualizar todo lugar que hoje lê `RULES.md`** (ver
  `_perguntar` em `orchestrator.py`, que monta o system prompt com
  `SITES/<site>/RULES.md`) pra ler do Redis em vez do arquivo —
  remover a leitura de arquivo, não manter os dois caminhos "por
  garantia".
- [x] Se `_template/RULES.md` deixar de fazer sentido como modelo
  (porque o fluxo de preenchimento passa a ser via Redis, não copiar
  markdown), documentar isso ou remover o template também.

## Decisões (2026-07-27 — decidido por mim a pedido do usuário: "menor atrito, mais simples, mais compatível com o projeto")

- **Schema: hash Redis simples por site**, não `SearchIndex`/vetor. Não
  é busca semântica — é leitura direta por site (`cliente:<slug>:perfil`
  com campos público-alvo, orçamento, ROAS-alvo, produtos, quem é o
  cliente, o que vende, pra quem vende). Mais simples que reusar o
  índice vetorial do `discover_tool`, que resolve um problema diferente
  (busca por relevância, não lookup direto).
- **Mesma instância/infra Redis do plano de fusão** — um Redis Cloud só
  pro projeto (já é o que existe hoje, `REDIS/.env` compartilhado),
  schema isolado por prefixo de chave (`cliente:*` vs `conversas:*` vs
  `tools_catalog`), sem motivo pra separar instância.
- **Saída da pesquisa de técnica: tarefa via `registrar_pedido_futuro`
  por padrão**, não spec markdown automático. Spec markdown (como o
  SKAG) continua existindo como passo manual pra quando a mudança for
  grande o bastante pra precisar de desenho — mas o caminho padrão,
  automatizado, é virar tarefa rastreável direto, mais simples e já
  usa o mecanismo que o projeto já tem.
- **Pesquisa usa o web search nativo da API Anthropic** (server tool do
  `anthropic` SDK), não Firecrawl. `elis_orchestrator.py` já chama
  `anthropic.Anthropic` diretamente — adicionar o tool nativo de busca
  na lista de tools do agente é a integração mais compatível com o que
  já existe (zero dependência nova); Firecrawl é ferramenta desta sessão
  de desenvolvimento (Claude Code), não algo que o bot em produção tem
  acesso hoje.
- **Ordem com os outros planos:** depende do plano de fusão só pela
  infra Redis compartilhada (schema, não código) — pode ser
  implementado depois da fusão criar a base de memória em Redis, ou em
  paralelo se o hash de perfil for criado de forma independente do
  índice de conversas. Sem dependência com os outros 2 planos.

## Como o dado real do perfil é coletado (definido com o usuário em 2026-07-27)

Duas fontes, combinadas:

1. **Análise do site online** — o que dá pra inferir sozinho, sem
   depender de ninguém: catálogo de produtos (já existe
   `TOOLS/CATALOGO/catalogo_produtos`), categorias, faixa de preço,
   indício de público (linguagem do site, linhas de produto). Cobre
   parte de "o que ele vende" e ajuda a rascunhar "pra quem vende".
2. **Conversa via Telegram com o gestor** — pro que só o gestor sabe
   (ROAS-alvo, orçamento diário real, público-alvo pretendido, quem é o
   cliente por trás do site). O agente conversacional pergunta o que
   falta, o gestor responde em linguagem natural, o agente extrai e
   grava no Redis.

**Consequência de arquitetura:** isso é uma capacidade nova do agente
fundido (plano `2026-07-27-fusao-agente-fluxo-conversa.md`) — um fluxo
de "montar/completar perfil de cliente" que mistura tool de leitura
(análise do site) com pergunta direta ao humano, e usa o mesmo agente
especialista de extração de contexto já desenhado nesse plano pra
transformar a resposta livre do gestor em campos estruturados no hash
Redis. Não precisa de sessão de levantamento manual à parte — o
levantamento acontece dentro da conversa normal do bot.

**Gatilho: sob demanda, não proativo** (mesmo princípio de menor atrito
já aplicado nas outras decisões) — o agente só pergunta um campo do
perfil quando uma tarefa real precisa dele e ele está vazio no Redis,
em vez de forçar uma entrevista completa na primeira vez que o site é
selecionado. Menos fricção pro gestor, e o perfil vai se completando
organicamente conforme o uso real do bot precisa dos dados.

## Arquivos alterados (implementação, 2026-07-27)

- **Create** `AGENTES/julio/perfil_cliente.py` — hash Redis por site
  (`cliente:<slug>:perfil`), 7 campos (`CAMPOS`): os 4 do template antigo
  + `quem_e_cliente`/`o_que_vende`/`pra_quem_vende` que a Elis pediu.
  `carregar`, `salvar_campo`, `campos_faltando`.
- **Modify** `AGENTES/julio/orchestrator.py` — `_sistema()` monta o
  bloco de site a partir do perfil em Redis (não mais `RULES.md`),
  informando ao modelo quais campos faltam e a regra de só perguntar
  quando uma tarefa real precisar. 2 tools novas, só disponíveis com
  site selecionado (`_ferramentas_site()`): `atualizar_perfil_cliente`
  (grava um campo que o humano confirmou) e `pesquisar_tecnica_campanha`
  (web search nativo da API Anthropic — `web_search_20250305` — resume
  em até 5 recomendações e registra como tarefa via `pedidos.registrar`,
  o mesmo mecanismo de `registrar_pedido_futuro`).
- **Modify** `AGENTES/julio/julio_config.py` — removido
  `regras_negocio()` (lia `RULES.md`, não é mais chamado por nada).
- **Delete** `SITES/{3gfoods,adoro,integrafoods,_template}/RULES.md` —
  vazios, substituídos pelo perfil em Redis (legado removido de
  verdade, não só parado de usar).

## Testado de verdade (2026-07-27, contra Redis/Anthropic reais)

- `atualizar_perfil_cliente`: mensagem "quero falar da adoro" → modelo
  chamou `selecionar_site` sozinho (texto livre, sem número); "o ROAS
  alvo da adoro é 4x, pode anotar" → modelo chamou
  `atualizar_perfil_cliente` → confirmado lendo direto do Redis
  (`perfil_cliente.carregar("adoro")` devolveu `{"roas_alvo": "4x"}`).
- `pesquisar_tecnica_campanha`: "pesquisa técnicas novas de negative
  keywords pra ecommerce de alimentos" → chamou `web_search` de
  verdade, devolveu 5 recomendações reais e específicas (termos de
  receita/delivery a negativar, listas por nível conta/campanha, tipo
  de correspondência) → confirmado que a tarefa foi escrita em
  `data/pedidos-futuros.md` de verdade.
- Chaves de teste e o registro de teste no backlog foram removidos
  depois (Redis e arquivo local, ambos limpos).
