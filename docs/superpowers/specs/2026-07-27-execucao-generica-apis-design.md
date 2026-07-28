# Execução genérica de APIs — princípio do projeto (não só ADWORDS)

## Contexto

Sessão de 2026-07-27 (rearquitetura, rodada 2 — ver
`ARQUITETURA/entendimento.md` e `ARQUITETURA/contrato-tool-agente.md`).
Depois de corrigir o bidding de `criar_campanha` (achado: tool
decidindo estratégia por conta própria) e testar dois casos reais que
quebraram a correção duas vezes seguidas — "segmentação por CEP" e
"público que entrou num funil de venda X" — ficou claro que o problema
não é falta de um parâmetro específico, nem falta de decompor uma tool
grande em tools menores. É que **qualquer conjunto FIXO de tools
curadas, por mais bem desenhado, vai sempre ficar um passo atrás do
próximo pedido não previsto**. O usuário foi explícito: quer "uma
ferramenta de IA inteligente e dinâmica capaz de entender e se
adaptar, não uma série de funções mocadas" — e que isso vale pro
projeto INTEIRO (Ads, GA4, GTM, Search Console), não só ADWORDS.

## Objetivo

Substituir o modelo de "uma tool curada por capacidade" (ex:
`criar_campanha`, `analise_ads`) por um modelo de **execução genérica
por plataforma**: um pequeno número de primitivas (consultar schema
real, executar mutação genérica, executar consulta genérica) que
mapeiam direto na forma real de cada API do Google. O agente constrói
a operação exata que precisa, informado pela consulta de schema ao
vivo — a mesma coisa que o Claude já demonstrou fazer corretamente
nesta sessão (corrigiu o bug de `explicitly_shared` lendo a doc real,
desambiguou entre 4 tools parecidas usando só a description).

## Princípio central

**Curadoria de tool por capacidade específica não escala** — o espaço
de pedidos de marketing é aberto por natureza (qualquer critério de
segmentação, qualquer tipo de recurso, qualquer relatório). Ao invés
de enumerar capacidades uma por uma (por mais genérico que o parâmetro
de cada uma seja), a arquitetura expõe a FORMA da API real
(recursos/operações/consultas) e deixa a inteligência de "o que
construir pra este pedido" inteiramente com o agente.

**O que ISSO NÃO significa:** não é "jogar a API crua pro agente sem
nenhuma estrutura". Continua havendo: schema real consultável (não
adivinhação), validação antes de gastar uma chamada real
(`validate_only`/equivalente), confirmação humana obrigatória antes de
qualquer mutação, e guardrails de segurança de negócio que nenhum
prompt ou decisão do agente pode sobrepor (ex: campanha sempre nasce
PAUSADA). O contrato tool↔agente continua valendo — só que agora a
"tool" é o mecanismo genérico de execução, e a "decisão" do agente
inclui não só valores de parâmetro, mas a própria escolha de QUAL
operação da API chamar.

## Arquitetura — o padrão, repetido por plataforma

Cada plataforma (`ADWORDS`, `GA4`, `GTM`, `SEARCH_CONSOLE`) ganha o
mesmo conjunto de 2-3 primitivas genéricas em vez de tools por
capacidade:

### ADWORDS (primeira aplicação — já tem doc oficial coletada e testada nesta sessão)

- **`ads_consultar_schema(tipo_recurso)`** — devolve os campos reais de
  qualquer tipo de recurso/mensagem da API (Campaign, CampaignBudget,
  AdGroupCriterion, UserList, etc.), via introspecção do pacote
  `google-ads` instalado (mesma técnica usada em
  `TOOLS/ADWORDS/DOCS/raw/mutate_mensagens.json` — vira consulta ao
  vivo, não só arquivo estático).
- **`ads_mutate(recurso, operacao, campos)`** — cria/atualiza/remove
  QUALQUER tipo de recurso. Substitui `criar_campanha` como o
  mecanismo de escrita.
- **`ads_gaql(query)`** — consulta de leitura arbitrária (GAQL),
  complementando as tools de análise curadas que já existem.

### GA4

- **`ga4_consultar_schema()`** — dimensões/métricas reais da
  propriedade, via `getMetadata` (discovery document em runtime, mais
  direto que Ads).
- **`ga4_report(dimensoes, metricas, filtros, periodo)`** — `runReport`
  genérico.
- **`ga4_admin_mutate(recurso, operacao, campos)`** — a API Admin do
  GA4 tem operações de escrita reais (dimensão customizada, evento de
  conversão, etc.) — mesmo padrão de `ads_mutate`.

### GTM

- **`gtm_consultar_schema()`** + **`gtm_mutate(recurso, operacao, campos)`**
  — a API do GTM já é CRUD por natureza (tags, triggers, variáveis,
  versões), encaixa direto no padrão.

### SEARCH_CONSOLE

- **`search_console_consultar_schema()`** + **`search_console_query(...)`**
  — searchAnalytics, sitemaps, inspeção de URL.

## O que continua curado (regra, não exceção platform-specific)

Só tools que encapsulam **cálculo ou lógica de negócio real e
reutilizável** — não uma decisão que o agente deveria fazer sozinho.
Exemplo já existente: `analise_ads`/`analise_vendas` cruzam Ads+GA4
pra calcular CAC-blended — isso é lógica de negócio genuína (a fórmula
de cruzamento), não uma escolha estratégica escondida. Critério
prático: **se a tool só "cria/altera um recurso" ou "consulta dado
bruto" — sempre genérico. Se a tool faz um CÁLCULO ou CRUZAMENTO
específico que tem valor por si só, reutilizável — pode continuar
curada.**

## Guardrails obrigatórios (código, nunca prompt — mesmo princípio em qualquer plataforma)

1. Toda mutação (`*_mutate`) é `requer_confirmacao=true`,
   incondicionalmente.
2. Antes de qualquer mutação real ser efetivada, roda um dry-run
   automático (`validate_only` no Ads; equivalente nas outras APIs
   quando existir) — vira a rede de segurança genérica, substituindo
   os checks manuais por tool que não generalizavam
   (`validar_proposta.py` de `criar_campanha`).
3. Invariantes de segurança de negócio ficam hardcoded no executor
   genérico daquela plataforma — nunca dependem do agente lembrar de
   pedir certo. Ex: `ads_mutate` força `status=PAUSED` em qualquer
   `create` do recurso `Campaign` especificamente, sem exceção, mesmo
   que o agente não peça isso explicitamente (mesmo guardrail que já
   existia em `construtor.py`, agora aplicado no executor genérico em
   vez de codificado dentro de uma tool específica).
4. Escopo por site continua igual ao que já existe no núcleo v2 (um
   site por execução, nunca cruzar sites).

## Como isso se encaixa no que já foi construído

`ARQUITETURA/nucleo/agente.py` (o loop de tool-calling) **não muda** —
ele já suporta sequências arbitrárias de chamadas de tool no mesmo
turno (validado nos testes de hoje). `executor_tools.py`
(`criar_executor_tool`) também não muda estruturalmente — continua
despachando por `tool.json` (script + modo_entrada); só os SCRIPTS por
trás mudam de "um script por capacidade" pra "um script genérico por
primitiva" (`ads_mutate.py`, `ads_consultar_schema.py`, `ads_gaql.py`).
O contrato de validação (`validacao_tool.py`) continua sendo usado do
mesmo jeito — antes de qualquer tool `requer_confirmacao` virar
pendência.

## Migração

- `TOOLS/ADWORDS/criar_campanha/` é **movido pra pasta de referência**
  (mesmo padrão já combinado pro núcleo v2 — nunca deletado direto,
  vira referência do que já funcionava) e **retirado do catálogo ativo**
  — não fica rodando em paralelo com `ads_mutate` (dois caminhos pra
  criar campanha é exatamente o tipo de confusão que essa
  rearquitetura existe pra evitar).
- `TOOLS/ADWORDS/analise_ads`, `analise_vendas` (GA4/ADWORDS/Search
  Console) — mantidas, por encapsularem cálculo real (ver regra
  acima).
- GA4/GTM/Search Console: hoje só têm tools de análise/leitura — os
  genéricos de mutate (`ga4_admin_mutate`, `gtm_mutate`) são
  capacidade NOVA, não substituição de nada existente.

## Ordem de implementação sugerida

1. **ADWORDS primeiro** — já tem doc oficial coletada
   (`TOOLS/ADWORDS/DOCS/raw/mutate_*.json`) e testes reais rodados
   nesta sessão (Smart Bidding, desambiguação). Menor distância entre
   "o que já existe" e "o que este design pede".
2. GA4 — tem discovery document em runtime (mais simples de
   introspectar que Ads), e já tem uso ativo (perfil de cliente,
   análises).
3. GTM, Search Console — mesmo padrão, ordem menos crítica.

## Testes

Mesma disciplina já estabelecida nesta sessão:
- Testes mecânicos com `fake_anthropic` (Plano 1) — script genérico
  real rodado via subprocess com dado de teste em `tmp_path` (mesmo
  padrão de `test_executor_tools.py`), provando que `ads_mutate`/
  `ads_consultar_schema`/`ads_gaql` despacham certo pro tipo de
  recurso/operação pedido.
- **Pelo menos 1 teste REAL (não mock)** por primitiva nova, provando
  que o Claude de verdade consegue: consultar o schema de um recurso
  que não foi mencionado nesta sessão (evitar viés de "só testei o que
  já expliquei pra ele"), montar um `ads_mutate` válido, e o
  `validate_only` aceitar sem erro — replicando a disciplina que já
  rendeu 2 achados reais hoje (bug do orçamento compartilhado,
  desambiguação entre tools parecidas).
