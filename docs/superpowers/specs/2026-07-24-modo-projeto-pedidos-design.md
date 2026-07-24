# Modo Projeto + Pedidos do Gestor — Design

Data: 2026-07-24
Status: aprovado, pronto pra virar plano de implementação

## Contexto

O sistema completo (seleção de site + tools reais de marketing) ainda
não está maduro o bastante pra ser a experiência padrão do bot no
Telegram. O gestor (Leandro/Marduka, chat_ids já autorizados em
`REDIS/.env`) precisa conseguir conversar com o Julio agora mesmo pra
entender o que já foi construído, tirar dúvidas, e registrar pedidos de
mudança/funcionalidade — sem passar pelo fluxo de site/tools de
marketing, que não é o propósito dessa conversa.

Isso amarra duas coisas que já existiam soltas no projeto:
- `REDIS/planejador/` e `REDIS/coder/` (spec
  `2026-07-22-planejador-coder-design.md`) — prontos, mas sem
  orquestração automática de principio a fim (fora de escopo daquela
  spec, de propósito).
- O próprio `orchestrator.py` do Julio, que hoje só sabe conversar
  sobre marketing de um site escolhido.

## Objetivo

1. **Modo projeto**: um flag global (`MODO_PROJETO=1` em `REDIS/.env`)
   que desvia o bot inteiro pra um modo de conversa focado em explicar o
   projeto e registrar pedidos — sem menu de site, sem tools de
   marketing. Desligar o flag volta ao comportamento atual, sem
   alteração de código.
2. **Pedido de projeto → rascunho técnico automático**: quando o gestor
   descreve algo que quer mudar/adicionar, o Julio salva o pedido e
   dispara Planejador → Coder automaticamente, mas o resultado vai pra
   uma branch git nova (`pedido/<id>`) — **nunca em `master`**, nunca dá
   push nem deploy sozinho. `master` (o que está rodando ao vivo) fica
   intocado.
3. Apresentação em linguagem simples pro gestor: sem jargão técnico
   (branch, commit, etc.) nas respostas do Julio.

## Fora de escopo (nesta v1)

- Push automático da branch pro remoto — a deploy key na EC2 hoje é
  somente-leitura (ver `infra/ec2/README.md`). A branch fica local, no
  host onde o bot está rodando; revisão e merge continuam manuais
  (Eduardo ou uma sessão Claude Code busca a branch depois).
- Deploy automático do rascunho.
- Rodar tarefas em paralelo — Planejador e Coder já são chamadas
  síncronas (mesmo padrão da spec anterior); a execução de um pedido
  roda tarefa por tarefa, em sequência, dentro do próprio handler da
  mensagem do Telegram (pode demorar dezenas de segundos a poucos
  minutos — aceitável no volume de uso esperado nesta fase).
- Detecção automática de "isso parece um pedido de projeto" fora do
  modo projeto — o modo é ligado/desligado no nível do bot inteiro, não
  por mensagem.

## Arquitetura

### 1. Flag de modo (`julio_config.py`)

```python
def modo_projeto() -> bool:
    return os.getenv("MODO_PROJETO", "").strip() == "1"

def status_projeto_md() -> Path:
    return PACKAGE_ROOT / "STATUS_PROJETO.md"
```

### 2. `AGENTES/julio/STATUS_PROJETO.md` (novo)

Documento em linguagem simples (não o jargão H/I/P/R de
`entendendno.md`): o que é o projeto, o que já funciona de verdade hoje
(as 7 tools reais por plataforma, os 3 sites atendidos), o que está
pendente (GTM ainda não conectado ao Julio, catálogo de produtos da 3G
historicamente ruim, etc.). Mantido por Eduardo/Claude Code conforme o
projeto avança — é o "livro" que o Julio usa como contexto fixo no
modo projeto, igual `GLOBAL.md`/`RULES.md` hoje.

### 3. `AGENTES/julio/orchestrator.py`

No topo de `processar_mensagem`, antes de qualquer outra checagem:

```python
if config.modo_projeto():
    return _processar_modo_projeto(chat_id, texto, telegram_transport)
```

`_processar_modo_projeto`:
- Estado próprio, arquivo separado (`data/conversas_projeto/<chat_id>.json`,
  só `historico` — sem site/proposta pendente, não reaproveita o
  estado do modo normal pra não misturar os dois fluxos se o flag for
  ligado/desligado no meio do uso).
- `/start` manda uma saudação curta explicando que o bot está em modo
  de apresentação do projeto, sem menu de site.
- Conversa livre com Claude: `system` = conteúdo de `STATUS_PROJETO.md`
  + instrução de personalidade (reaproveita `GLOBAL.md`, a seção de
  comportamento vale igual) + regra de quando chamar cada tool abaixo.
- Duas tools disponíveis (schemas em `orchestrator.py`, mesmo padrão
  das tools de marketing hoje):
  - `registrar_pedido_projeto(pedido, contexto="")` — chamar quando o
    gestor descrever algo que quer mudar/adicionar (não pra perguntas
    sobre o que já existe).
  - `listar_pedidos_projeto()` — chamar quando o gestor perguntar pelo
    status de pedidos já feitos.
- Loop de tool-use: mesmo padrão de `_perguntar` (até
  `MAX_TURNOS_FERRAMENTA` rodadas), mas simplificado — sem
  `requer_confirmacao` (essas duas tools nunca pedem confirmação humana
  antes de rodar, ao contrário de `criar_campanha`).

### 4. `AGENTES/julio/pedidos_projeto.py` (novo)

- `registrar(pedido: str, contexto: str = "") -> dict`: gera um `id`
  curto (`uuid4().hex[:8]`), salva
  `data/pedidos_projeto/<id>.json` (`{id, pedido, contexto, status:
  "registrado", criado_em, branch: None, tarefas: None, erro: None}`),
  devolve o registro. **Chama `executar()` em seguida, na mesma
  chamada** (sem fila separada — é o próprio fluxo síncrono do handler
  do Telegram).
- `executar(pedido_id: str) -> dict`:
  1. `git status --porcelain --untracked-files=no` no `HUB_ROOT` — se
     sujo (mudança não commitada em arquivo rastreado), aborta com
     `erro` sem mexer em nada (guardrail: nunca assume que pode
     descartar trabalho em andamento).
  2. `git checkout -b pedido/<id>`.
  3. `Planejador().planejar(pedido)` → lista de tarefas.
  4. Pra cada tarefa: `Coder().implementar(tarefa)`, acumula resultado.
  5. `git add -A && git commit -m "Pedido <id>: <resumo>"` — só se pelo
     menos uma tarefa foi escrita; senão pula commit.
  6. **`finally`**: `git checkout master` sempre roda, mesmo se algum
     passo acima falhar — garante que o working tree que o bot
     realmente usa (import, leitura de arquivos) volta pro estado de
     produção. Se o `checkout -b` do passo 2 nunca aconteceu, esse
     `checkout master` é no-op seguro (já está em master).
  7. Atualiza o JSON do pedido: `status` vira `"rascunho_pronto"` (com
     `branch` e lista de tarefas/resultados) ou `"erro"` (com `erro`
     preenchido) se qualquer passo crítico falhar.
- `listar() -> list[dict]`: lê todos os JSON de
  `data/pedidos_projeto/`, ordenado por `criado_em`.

Subprocess `git` sempre com `cwd=HUB_ROOT`, `check=False` (trata
retorno não-zero explicitamente, nunca deixa exceção genérica de
subprocess estourar sem contexto).

### 5. Tradução pro gestor (dentro de `orchestrator.py`)

Depois de `registrar()` + `executar()`, o resultado (JSON técnico) vira
`tool_result` pro Claude formular a resposta final em português simples
— nunca menciona "branch"/"commit"/"git" na resposta, algo como:

> "Anotado! Já deixei um rascunho técnico preparado — a equipe vai
> revisar antes de colocar no ar."

Ou, se `status == "erro"`:

> "Anotei seu pedido, mas não consegui preparar o rascunho técnico
> agora — vou registrar pra alguém da equipe olhar."

`listar_pedidos_projeto` mapeia `status` pra texto simples: `registrado`
→ "na fila", `rascunho_pronto` → "rascunho pronto pra revisão",
`erro` → "registrado, precisa de atenção manual".

## Erros

- Working tree sujo antes de `executar()`: aborta sem tocar em nada,
  pedido fica com `status: "erro"`, mensagem genérica (não expõe git
  pro gestor).
- Falha em qualquer chamada de LLM (Planejador/Coder): já tratada
  dentro deles (`erro` no dict de retorno da tarefa) — `executar()`
  segue pras próximas tarefas, não aborta o pedido inteiro por uma
  tarefa falhar.
- Falha de `git checkout`/`commit`: captura `subprocess`, marca pedido
  como erro, tenta `git checkout master` mesmo assim no `finally`.

## Teste

Sem suite automatizada (mesmo padrão do projeto). Verificação manual:
(a) com `MODO_PROJETO=1`, `/start` no Telegram não deve mostrar menu de
site; (b) pedir "quero que o bot também me avise quando uma campanha
gastar mais que o orçamento" deve gerar uma branch `pedido/<id>` local
com pelo menos um arquivo alterado, working tree volta pra `master`
depois, e a resposta ao gestor não menciona jargão git; (c) perguntar
"como estão meus pedidos" deve listar o pedido anterior com status em
português simples.
