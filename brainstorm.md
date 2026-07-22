# Brainstorm — Agente de Marketing Digital (Ads + GTM + Analytics + SEO)

> Baseado na análise de `C:\INTEGRAFOODS\teste\GADS\agente-cmo` (o teste mencionado no CLAUDE.md) —
> esse projeto já está mais maduro do que parece: tem coleta, análise com Claude, execução com
> guardrails, fila de aprovação e bot de Telegram, tudo funcionando para o Google Ads da 3G Foods.
> O brainstorm abaixo parte dessa base e foca no que falta: **GTM, Analytics e Search
> Console/SEO/performance**.

---

## 1. O que já existe (reaproveitar, não recriar)

| Peça | Onde | Status |
|---|---|---|
| Coleta de métricas (GAQL, 30 dias) | `src/collector.py` | ✅ Funciona |
| Análise com Claude + structured output | `src/analyst.py` | ✅ Funciona (schema JSON rígido) |
| Execução com guardrails (teto de gasto, %/dia, fila de aprovação) | `src/executor.py` | ✅ Funciona |
| Criação de campanhas via chat (Telegram) | `src/telegram_bot.py` + `campaign_builder.py` | ✅ Funciona |
| Relatório diário (arquivo + Slack/Telegram/e-mail) | `src/reporter.py` | ✅ Funciona |
| Briefing de negócio e regras invioláveis | `agente-cmo/CLAUDE.md` | ⚠️ Ainda com placeholders "(AJUSTAR)" |
| Credenciais Google Ads (3G Foods) | `.env` + `docs/setup-do-zero-checklist.md` | ✅ **Basic Access aprovado** — developer token liberado |
| Automação recorrente | `.github/workflows/agente-cmo.yml` | ✅ Existe (diário 8h BRT) |

**Destravado:** com o Basic Access aprovado, o agente já pode rodar de verdade contra a conta da
3G Foods (antes só funcionava em modo teste). Próximo passo natural é a Fase 5 do guia — rodar
`--dry-run` por 1-2 semanas antes de liberar `--executar`, já que isso ainda não foi validado em
produção.

**Só cobre 1 dos 3 sites hoje** (3G Foods, customer_id 758-019-9564). Integra Foods e Adoro/Conge
ainda não têm conta Ads configurada no agente.

---

## 2. O eixo que falta: GTM + GA4

Você descreveu o objetivo com precisão — o agente deve conseguir **acessar, verificar, propor e
alterar** as três pernas (GTM, GA4, Ads), não só otimizar lances. Isso implica duas APIs novas:

- **Google Tag Manager API** (`tagmanager.googleapis.com`) — ler/editar containers, tags, triggers,
  variáveis, versões, publicar.
- **Google Analytics Admin API + Data API** (GA4) — ler configuração (data streams, eventos
  marcados como conversão, custom dimensions) e ler dados (para saber se o tracking está
  realmente registrando).

### 2.1 Auditor de GTM (`src/gtm_auditor.py` — novo módulo)

Ideia: um módulo que roda **read-only** primeiro (mesmo espírito do `--dry-run` do Ads) e produz um
relatório de saúde do container:

- Tags sem trigger associado (tag "morta")
- Triggers apontando para eventos que não existem mais no site
- Tag de conversão do Google Ads existe e está publicada na versão live (não só no draft)
- Variáveis de datalayer usadas nas tags realmente existem no `dataLayer.push` do site
- Comparação entre workspace/draft e container publicado (mudanças pendentes de publicar)

**Ponto de decisão do usuário:** o GTM não tem "GAQL" — a auditoria de datalayer real exige rodar o
site (headless browser) e capturar os eventos disparados, ou confiar só na configuração estática do
container. Isso é uma escolha de arquitetura:
- Estático (só ler config do GTM) → mais simples, mas não pega bugs de implementação no site
- Dinâmico (Playwright/Chrome DevTools navegando o site e capturando `dataLayer`) → mais fiel à
  realidade, mas mais caro/lento e exige manutenção por site

### 2.2 Auditor de GA4 (`src/ga4_auditor.py` — novo módulo)

- Verificar que o `measurement_id` do data stream bate com o que está implementado no GTM/site
- Listar eventos marcados como conversão e comparar com as conversões importadas no Google Ads
  (evitar o clássico erro de dupla contagem ou conversão não importada)
- Checar se enhanced e-commerce / eventos de `purchase` têm os parâmetros obrigatórios
  (`value`, `currency`, `transaction_id`) — comum em e-commerce de carnes com ticket variável por peso
- Detectar quedas anômalas de eventos (ex: `add_to_cart` caiu 80% numa semana → GTM provavelmente
  quebrou, não é problema de campanha)

### 2.3 Conciliação entre as 3 pernas (o valor real do "agente CMO completo")

O ganho de ter os três conectados não é auditar cada um isolado — é **cruzar**:

> "ROAS da campanha X caiu" → o agente já teria como primeiro passo de diagnóstico verificar
> "o GA4 registrou os eventos de conversão dessa campanha nesse período?" antes de sugerir pausar
> keyword. Se o problema for tracking quebrado (GTM não publicado, tag GA4 apontando pro
> measurement_id errado), a ação certa é **alertar sobre tracking**, não mexer em lance.

Isso é uma extensão natural do `analyst.py`: hoje ele só recebe dados do Ads. O prompt evolui para
receber também `status_tracking` (resumo do GTM+GA4) e a lista de ações ganha uma nova categoria,
por exemplo `acao: "alertar_tracking_quebrado"`, que **nunca** é auto-executável — sempre vai para
alerta humano, porque mexer em tracking tem risco de perder dados históricos.

---

## 3. Search Console + SEO + performance do site

Esse eixo é diferente dos dois anteriores: Ads/GTM/GA4 são sobre tráfego pago e tracking; Search
Console é sobre **tráfego orgânico e saúde técnica do site** — mas se conecta ao resto porque
páginas com SEO ruim ou performance ruim também prejudicam o Quality Score do Ads e a experiência
que gera a conversão que o GA4 está tentando medir.

### 3.1 Auditor de Search Console (`src/search_console_auditor.py` — novo módulo)

API: **Search Console API** (`searchconsole.googleapis.com`), read-only por natureza (não existe
"executar ação" no Search Console — é 100% diagnóstico/indexação):

- Páginas com erros de indexação (`Coverage`/`Inspection API`) — página existe mas o Google não
  indexou, comum depois de mudanças de URL sem redirect
- Quedas de cliques/impressões por página ou por query (mesma lógica de "anomalia" do GA4, mas do
  lado orgânico) — separa se a causa é sazonal (ex: queda de busca por "picanha" fora de churrasco)
  ou técnica (página caiu do índice)
- Queries com impressão alta e CTR baixo → oportunidade de melhorar título/meta description (dá pra
  o Claude sugerir reescritas, já que ele lida bem com copy)
- Core Web Vitals / `Inspection API` (mobile usability, indexação mobile-first) por página-chave
  (home, categorias, produtos mais vendidos)
- Sitemap: status de envio e erros de processamento

### 3.2 Onde isso cruza com Ads/GTM/GA4

- **Página de destino de anúncio com problema de indexação/velocidade** também é sinal de alerta
  para o `analyst.py` — CPC pode estar caro por Quality Score baixo, e a causa raiz pode ser a
  landing page, não o lance.
- **Produto com boa posição orgânica e boa conversão** é candidato natural a *reduzir* investimento
  em Ads para aquela keyword específica (o orgânico já está resolvendo) — redistribuir orçamento
  para termos sem cobertura orgânica.
- Isso fecha o ciclo "CMO completo": pago (Ads), tracking (GTM/GA4) e orgânico (Search Console)
  informando a mesma camada de decisão.

### 3.3 Guardrail natural

Diferente de GTM/Ads, aqui não existe risco de "executar ação errada" — é só leitura e sugestão.
O risco é outro: **recomendação de conteúdo/SEO mal calibrada** (ex: sugerir reescrever um título
que já rankeia bem). Por isso, ações de SEO devem sempre virar `alertas`/sugestões no relatório,
nunca `acoes` auto-executáveis — não tem "aprovação de baixo risco" aqui, é sempre humano decidindo
o que publicar no site.

---

## 4. Extensão de guardrails para GTM/Analytics

Os guardrails atuais do `executor.py` são pensados para dinheiro (gasto, %/dia). GTM/GA4 precisam de
guardrails de **outro tipo de risco**: perda de dados de tracking é irreversível (não dá pra
recuperar conversões não registradas).

Ideia de regra para o `CLAUDE.md` do agente:

```
# Guardrails de Tracking (GTM/GA4)
- NUNCA publicar uma versão do GTM automaticamente — sempre propor o diff e aguardar aprovação
- NUNCA remover uma tag ou trigger — só desativar (pausar), remoção é manual
- Qualquer mudança em tag de conversão (Ads ou GA4) exige aprovação humana, mesmo de baixo "impacto"
- Auditoria roda em modo leitura por padrão; escrita no GTM é sempre um `--dry-run` até 2ª fase
```

Aqui está um trecho pequeno (~8 linhas) que vale você mesmo escrever, porque é uma decisão de
negócio, não técnica: **qual o limite de "queda de eventos" que dispara alerta automático?** Ex.: se
`purchase` cair mais de X% dia-a-dia comparado à média móvel de 7 dias, o agente alerta. Esse
threshold depende de quão sazonal é a demanda dos seus produtos (carnes/proteína costuma ter picos
em datas específicas), então é você quem tem o contexto pra calibrar isso — não tem resposta
"correta" genérica.

---

## 5. Arquitetura multi-site

Hoje o `.env`/`CLAUDE.md` do `agente-cmo` são de 1 conta só. Para os 3 sites, duas abordagens:

- **Opção A — 1 config por site:** pasta `sites/integrafoods/`, `sites/3gfoods/`, `sites/adoro/`,
  cada uma com seu `.env` (customer_id do Ads, container ID do GTM, property ID do GA4, site
  verificado no Search Console) e seu bloco de regras de negócio (nicho, ticket médio, ROAS mínimo
  variam por marca). `main.py --site 3gfoods`.
- **Opção B — 1 execução, N contas:** o agente itera as 3 contas no mesmo processo, gera um
  relatório consolidado. Mais simples de operar, mas mistura guardrails/orçamentos diferentes num
  só lugar — arriscado se um site tiver regra de negócio muito diferente do outro.

Dado que o `.env` do agente-cmo já é 1:1 com uma conta, a Opção A é a extensão mais natural do que
já existe — reaproveita quase tudo, só precisa parametrizar `config.py` para carregar de
`sites/<nome>/.env` em vez de um `.env` fixo na raiz.

---

## 6. Roadmap sugerido (incremental sobre o que já existe)

1. **Curto prazo:** com o Basic Access já aprovado, rodar o agente Ads atual em `--dry-run` por
   2 semanas, como o próprio guia já recomenda — validar o que já foi construído antes de somar
   complexidade.
2. **GTM/GA4/Search Console read-only:** criar `gtm_auditor.py`, `ga4_auditor.py` e
   `search_console_auditor.py`, todos só de leitura, alimentando o `reporter.py` com seções "Saúde
   de Tracking" e "Saúde de SEO" no relatório diário. Zero risco, alto valor de diagnóstico — e o
   Search Console é o mais simples de somar primeiro, já que não tem ações executáveis.
3. **Conciliação:** cruzar alertas de tracking e SEO com decisões do `analyst.py` (não sugerir ação
   de Ads se o tracking daquela campanha estiver quebrado, ou realocar orçamento de keywords que já
   rankeiam bem no orgânico).
4. **Multi-site:** refatorar `config.py` para `sites/<nome>/` e rodar os 3 domínios.
5. **Escrita em GTM/GA4:** só depois de meses de operação estável do restante, com guardrails de
   não-remoção e aprovação obrigatória. Search Console segue sempre read-only/sugestão.
6. **Orquestração de agentes:** hoje cada auditor (Ads/GTM/GA4/Search Console) é um módulo isolado
   que eu preciso saber invocar na ordem certa. Criar uma camada de orquestração — um agente
   "maestro" que recebe o pedido em linguagem natural (ex: "audita o GTM da Integra Foods", como no
   `gtm-workflow.md`), decide quais módulos/skills chamar, resolve o site certo no registro
   multi-site (item 4) e junta os resultados num único relatório. É o que faz o resto fluir sem eu
   precisar lembrar qual script rodar pra cada tipo de pedido.

---

## 7. Perguntas em aberto (decisões suas, não técnicas)

- Auditoria de GTM: confiar na config estática ou navegar o site de verdade (Playwright) para
  validar o `dataLayer`? Isso muda custo e complexidade do `gtm_auditor.py`.
- Threshold de "queda de eventos" que dispara alerta automático por site (sazonalidade de carnes).
- Threshold de "queda de cliques/impressões orgânicas" que separa sazonalidade de problema técnico
  no Search Console.
- Multi-site: um `CLAUDE.md`/orçamento por marca (Opção A) ou operação consolidada (Opção B)?

---

## 8. Skills e plugins do Claude Code que aceleram esse desenvolvimento

Mapeamento de ferramentas **já disponíveis neste ambiente** para cada parte do trabalho acima —
evita reinventar coisa que o próprio Claude Code já resolve.

| Ferramenta | Onde ela ajuda no brainstorm | Como usar |
|---|---|---|
| **plugin `context7`** | Todas as APIs novas (§2, §3): GTM API, GA4 Admin/Data API, Search Console API mudam com frequência e seu treinamento pode estar desatualizado | Invocar antes de escrever cada `*_auditor.py` — pega docs/exemplos atuais em vez de confiar em memória |
| **skill `claude-api`** | `analyst.py` e `telegram_bot.py` já usam a Anthropic API (structured output, tool use); qualquer extensão do prompt para incluir `status_tracking` (§2.3) passa por aqui | Dispara automaticamente sempre que eu mexer em código que chama `anthropic.*` — garante schema/model id corretos |
| **plugin `chrome-devtools-mcp`** (skills `chrome-devtools`, `chrome-devtools-cli`) | Resolve diretamente o "Ponto de decisão" do §2.1 — capturar `dataLayer` de verdade navegando os 3 sites, sem escrever scraper do zero | `navigate_page` + `evaluate_script` (ler `window.dataLayer`) + `list_network_requests` (confirmar hit do GA4/Ads) por site |
| **plugin `playwright`** | Alternativa ao Chrome DevTools MCP para o mesmo problema, mais adequado se quiser rodar isso como script agendado (não interativo) em vez de sessão de debug | `browser_navigate` + `browser_evaluate` dentro do próprio `gtm_auditor.py`/`ga4_auditor.py` |
| **skill `superpowers:writing-plans` + `superpowers:executing-plans`** | Cada novo módulo (`gtm_auditor.py`, `ga4_auditor.py`, `search_console_auditor.py`, refatoração multi-site) é um pedaço de trabalho multi-etapa — vale planejar antes de codar em vez de ir direto | Um plano por módulo, com checkpoints de revisão antes de mexer em `executor.py`/guardrails |
| **skill `superpowers:dispatching-parallel-agents` / `subagent-driven-development`** | Os 3 auditores read-only (§6, item 2) são independentes entre si — candidatos naturais a implementar em paralelo | Um subagente por auditor, já que não compartilham estado |
| **skill `claude-md-management:claude-md-improver`** | Achei placeholders `(AJUSTAR)` pendentes em `agente-cmo/CLAUDE.md` (§1); e o plano multi-site (§5) vai gerar 3 `CLAUDE.md` por marca que precisam ficar consistentes | Rodar depois de preencher os valores reais do negócio, e de novo a cada novo `CLAUDE.md` por site |
| **plugin `telegram`** (skills `telegram:configure`, `telegram:access`) | `telegram_bot.py` hoje reimplementa na mão: polling, allowlist (`TELEGRAM_AUTHORIZED_CHAT_IDS`), estado de conversa em JSON — o plugin do Claude Code já resolve pairing/allowlist/policy | Avaliar migrar a autorização e o transporte para o plugin, mantendo só `campaign_builder.py` (lógica de negócio) como código próprio |
| **skill `schedule`** | Hoje a automação recorrente é só `.github/workflows/agente-cmo.yml` (§1) — a skill `schedule` cria/gerencia agentes em cron direto do Claude Code | Alternativa mais simples ao YAML manual para rodar `main.py --dry-run` diário, ou para rodar os auditores read-only em horário separado do Ads |
| **skill `dataviz` + `Artifact`** | `reporter.py` hoje só gera texto (§1) — os relatórios de "Saúde de Tracking"/"Saúde de SEO" (§6) ganham muito virando gráficos (queda de eventos, ROAS por site, cliques orgânicos) em vez de `.txt` | Gerar um Artifact/dashboard por execução, além (não em vez) do texto que já vai pro Slack/Telegram |
| **skill `pr-review-toolkit:code-reviewer` / `coderabbit:code-review`** | Guardrails (§4) são código de segurança — vale revisão extra antes de qualquer novo `_EXECUTORES` em `executor.py` ou antes de liberar escrita em GTM (§6, item 5) | Rodar review dedicado nesses módulos antes de tirar do `--dry-run` |
| **skill `fewer-permission-prompts`** | Desenvolvimento vai gerar bastante `python main.py --testar-conexao`, chamadas de API repetidas — fricção de permissão a cada comando | Rodar uma vez para gerar allowlist do projeto e destravar o ritmo de iteração |

**Onde eu não recomendo usar nada da lista:** UI/frontend (`shadcn`, `frontend-design`, `tailwindcss`)
— nada neste brainstorm pede interface web; o canal de interação já é Telegram/relatório, e um
dashboard visual (se vier a existir) é melhor resolvido com `Artifact`+`dataviz` do que com um app
frontend completo.
