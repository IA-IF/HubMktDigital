# Contrato Tool ↔ Agente

Regra obrigatória pra qualquer `TOOLS/**` — existente ou nova. Não é
uma preferência de estilo, é a causa raiz central de por que as tools
não funcionam direito hoje (ver `ARQUITETURA/entendimento.md`, seção
"O problema real das TOOLS").

## Princípio

**O agente projeta e decide a campanha (ou qualquer ação) inteira:
estratégia, valores-alvo, escolhas. A tool só executa fielmente esse
projeto.** Validação de entrada e garantia de compatibilidade técnica
com a API real são trabalho da tool. Decidir QUALQUER coisa
estratégica — mesmo que pareça pequena — nunca é.

## Regra prática (como reconhecer a violação)

Se, ao escrever ou revisar uma tool, uma linha de código escolhe um
comportamento estratégico sem que isso venha de um parâmetro de
entrada explícito — isso é um bug de fronteira de responsabilidade,
não um detalhe de implementação. Toda decisão estratégica precisa
estar refletida no `input_schema` como parâmetro (mesmo que opcional
com default), nunca escondida dentro do código da tool.

Teste rápido pra qualquer linha de código de uma tool: **"por que esse
valor específico, e não outro?"** Se a resposta é "porque o input pedia
isso" — ok, é execução fiel. Se a resposta é "porque eu (quem escreveu
a tool) achei que fazia sentido" — é uma decisão estratégica vazando
pro lado errado da fronteira.

## Sintoma de hoje (caso real, não hipotético)

`TOOLS/ADWORDS/criar_campanha` (commit `e37d881`): ao corrigir o
bidding `manual_cpc` (achado da auditoria contra a doc oficial) pra
Smart Bidding, o próprio corretor (eu) hardcoded
`campanha.maximize_conversions = {}` direto em `construtor.py`, sem
expor a escolha como parâmetro. Isso é exatamente a violação: a tool
tomou uma decisão estratégica (qual estratégia de lance usar, sem
alvo) que deveria ter vindo do agente — que, aliás, **já coleta esse
dado** (`roas_alvo` em `AGENTES/julio/perfil_cliente.py`, coletado de
verdade na conversa da 3G Foods nesta mesma sessão) e simplesmente não
tinha como passar isso pra tool. Dois lados do mesmo projeto, um
coletando informação que o outro não sabe receber.

Isso mostra que o erro se repete nos DOIS sentidos: a versão antiga do
código tinha ZERO estrutura (tudo por conta do julgamento solto do LLM
no prompt) — e um fix pontual meu, sem essa regra escrita, foi na
direção oposta igualmente errada (uma decisão fixa, sem parâmetro
nenhum). O contrato certo não é "menos decisão automática" nem "mais
decisão automática" — é **decisão sempre exposta como parâmetro,
execução sempre fiel a esse parâmetro**.

## Como aplicar daqui pra frente

Pra qualquer tool (existente ou nova), antes de qualquer outra
otimização:

1. Listar toda decisão que a tool toma hoje que NÃO vem de um
   parâmetro de entrada explícito.
2. Pra cada uma: virar parâmetro explícito no `input_schema`. Default
   só quando o default é puramente técnico/de compatibilidade da API
   (ex: `delivery_method=STANDARD`, `explicitly_shared=False` — detalhes
   de como a API espera o dado, não escolhas de negócio). Nunca um
   default que embute uma escolha estratégica escondida.
3. Nenhuma tool deve ter lógica do tipo "se o cliente tem X, usa
   estratégia Y" — esse é raciocínio do agente. A tool só recebe "usa
   estratégia Y" (já decidida) e executa.
4. Presunções de escopo do PROJETO (ex: geo=Brasil, idioma=PT-BR — os 3
   sites são todos brasileiros) são diferentes de estratégia de
   CAMPANHA — ainda vale listar essas separadamente e confirmar que
   são mesmo escopo fixo do projeto, não algo que devia variar por
   campanha/cliente.

## Impacto nos planos de otimização das TOOLS

Toda tool auditada (GA4, GTM, Search Console, e a revisão pendente do
próprio ADWORDS) precisa responder esta pergunta ANTES de qualquer
outra melhoria: **"essa tool decide algo que deveria vir do agente?"**
Se sim, essa é a PRIMEIRA correção — antes de otimizar uso de API,
antes de completude de campos, antes de qualquer outra coisa. Um plano
de auditoria de tool que não checa isso primeiro está incompleto.

## Consertos pendentes já identificados por essa regra

- `criar_campanha`: expor estratégia de lance como parâmetro —
  `roas_alvo_percentual` e/ou `cpa_alvo_brl`, opcionais, mapeando pra
  `target_roas`/`target_cpa`; ausência de ambos cai em
  `maximize_conversions` sem alvo (única opção segura sem histórico de
  conversão, não uma escolha estratégica escondida — é o "sem
  informação estratégica disponível ainda" explícito). Ainda não
  implementado — ver próxima sessão de trabalho.
- `criar_campanha`: negative keywords (`AdGroupCriterion.negative`) —
  a tool hoje nem ACEITA essa entrada, então o agente nem consegue
  decidir usar negativas ainda, mesmo que quisesse.
