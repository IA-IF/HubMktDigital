# Prático

Sites:

- https://integrafoods.ind.br/ — `C:\INTEGRAFOODS\www\web2` — **laboratório, começamos por aqui** — `SITE=integrafoods` — ✅ onboarded
- https://loja.3gfoods.com.br/ — `C:\INTEGRAFOODS\www\c3g-web` — `SITE=3gfoods` — ✅ onboarded (22/07/2026)
- https://loja.adoro.com.br/ — `C:\INTEGRAFOODS\www\adoro-web` — `SITE=adoro` — ✅ onboarded (22/07/2026).
  ⚠️ o código local está em pasta chamada `adoro-web` e o domínio antigo mencionado no `CLAUDE.md`
  original era `webadoro.conge.digital` — o domínio de produção real (confirmado via GTM/GA4/Search
  Console) é `loja.adoro.com.br`. Não confundir os dois.

Plataformas (ordem de trabalho):

## 1. Google Tag Manager (GTM)

Não é do zero — já existe container instalado no código do Integra Foods (`GTM-PJWJJHXR`, ver
`ssr-poc/src/config.js`), com tag do GA4 (`G-CC4D18ST42`), uma tag de e-commerce e variáveis de
dataLayer (`client_id`, `transaction_id`, `user_id`, `payment_type`) exportadas em
`C:\INTEGRAFOODS\www\web2\IA\GTM-PJWJJHXR_workspace7.json`.

**⚠️ Cuidado ao mexer no GTM do Integra Foods: existem 2 contas/containers na conta Google.**
`GTM-W6GWZX5` (conta "Integra Foods", domínio `www.integrafoods.ind.br`) é **LEGADO — ignorar,
não auditar, não mexer**. O container correto/ativo é `GTM-PJWJJHXR` (conta "IF V2", domínio
`ifv2.conge.digital`) — é esse que o `agente-gtm` usa.

O que falta criar/verificar:

- [x] Acesso ao container confirmado (22/07/2026, via navegador guiado) — `eduardo.rezende@integrafoods.ind.br`
      já tem nível "Publicação" no `GTM-PJWJJHXR`; workspace com 0 mudanças pendentes (sincronizado com o live)
- [x] Tag Manager API ativada no projeto `agente-cmo-ads-interno` e refresh_token gerado (22/07/2026)
- [x] **Primeira auditoria real rodada (22/07/2026)** — `agente-gtm/main.py --auditar`: 2 tags, 1 trigger,
      5 variáveis, tudo publicado, 0 tags sem trigger, 0 triggers órfãos, tag GA4 confere com `G-CC4D18ST42`
- [x] Tag GA4 disparando de verdade em produção — confirmado navegando analytics.google.com
      (22/07/2026): "coleta de dados ativa nas últimas 48 horas", eventos de funil e compras aparecendo
- [x] Tag de e-commerce cobre o funil todo — confirmado indiretamente pela auditoria GA4 (item 2):
      view_item, add_to_cart, begin_checkout e purchase todos com dados nos últimos 7 dias

## 2. Google Analytics (GA4)

Propriedade correta (confirmado 22/07/2026): conta **"Integra Foods"** (`233412801`), propriedade
**"IntegraFoods V2"** (`543849199`), stream "SSR" → `https://integrafoods.ind.br`. Measurement ID
`G-CC4D18ST42` — bate com o do GTM. Acesso já confirmado: `eduardo.rezende@integrafoods.ind.br` é
Administrador da propriedade.

**⚠️ A mesma conta "Integra Foods" tem várias outras propriedades** (3GFOODS, ADORO, CONGE,
CONGEv2, Devito, Dinamica) — não confundir pelo nome da conta, sempre usar o Property ID `543849199`.

Esqueleto criado em `agente-ga4/` (mesmo padrão do `agente-gtm`).

- [x] Acesso confirmado (22/07/2026, via navegador guiado)
- [x] Admin API + Data API ativadas no projeto `agente-cmo-ads-interno`, refresh_token gerado (22/07/2026)
- [x] **Primeira auditoria real rodada (22/07/2026)** — `agente-ga4/main.py --auditar`: "purchase" está
      marcado como conversão (junto com close_convert_lead, qualify_lead); funil dos últimos 7 dias sem
      nenhum evento zerado (440 page_view → 66 view_item → 11 add_to_cart → 24 begin_checkout → 2 purchase)

## 3. Search Console

Propriedade correta (confirmado 22/07/2026): `https://integrafoods.ind.br/` (URL-prefix property),
verificada, `eduardo.rezende@integrafoods.ind.br` é Proprietário. Sitemap `/sitemap.xml` enviado,
processado, 404 páginas encontradas, sem erros.

**⚠️ Existe também a propriedade do domínio antigo/staging `https://if-ssr.conge.digital/`**
(de antes da migração de domínio em 16/07/2026, ver `.trae/plans/migracao-dominio-integrafoods.md`
no repo do site) — não confundir, não mexer.

Esqueleto criado em `agente-search-console/` (mesmo padrão dos outros).

- [x] Acesso confirmado (22/07/2026, via navegador guiado)
- [x] Search Console API ativada no projeto `agente-cmo-ads-interno`, refresh_token gerado (22/07/2026)
- [x] **Primeira auditoria real rodada (22/07/2026)** — `agente-search-console/main.py --auditar`:
      sitemap com 0 erros/0 avisos, tráfego orgânico ativo nos últimos 28 dias (top query "integrafoods",
      9 cliques, posição média 1.8)

## 4. Google Ads

Já temos referência (`C:\INTEGRAFOODS\teste\GADS\agente-cmo`), hoje configurada pra 3G Foods.
Como o laboratório agora é o Integra Foods, o que falta criar:

**Decisão (22/07/2026): 1 conta Google Ads por site, todas dentro da mesma MCC** (`890-192-5637`,
"IF Apoio") — não uma conta unificada. Motivo: ROAS mínimo, margem e ticket médio são diferentes
por marca, e misturar sinais de produtos/públicos distintos numa conta só piora o smart bidding.

- **Contas existentes:** 3G Foods (`758-019-9564`) — já é cliente da MCC, já configurada no `agente-cmo`
- **⚠️ Achado ao investigar:** já existiam 2 contas Ads da Adoro na MCC/conta Google (não do Integra
  Foods como se pensava) — `510-339-3778` (Loja Adoro, completa) e `174-845-0313` (Loja Adoro,
  configuração incompleta/duplicada, decidimos ignorar por ora). Integra Foods realmente não tinha conta.

- [x] **Conta Google Ads do Integra Foods criada (22/07/2026)** — nome **"Integra Foods V2"**
      (mesmo padrão de nome do GTM/GA4, pra não confundir com legado), ID `332-316-6484`, vinculada
      à MCC `890-192-5637` (IF Apoio), faturamento configurado (perfil CONGE FOODS TECNOLOGIA E
      DISTRIBUICAO LTDA, Pix). Verificação de anunciante pendente (opcional, 1-10 dias, não bloqueia
      o setup de API) — ver tarefas em Admin da conta.
- [x] **Código replicado (22/07/2026)** — `agente-cmo` copiado para `agente-ads/` (mesmo padrão de
      nome dos outros agentes), sem tocar no original. `.env.example` já com `GOOGLE_ADS_CUSTOMER_ID`
      (`3323166484`) e `GOOGLE_ADS_LOGIN_CUSTOMER_ID` (`8901925637`) preenchidos.
- [x] **`.env` preenchido e conexão testada (22/07/2026)** — `python main.py --testar-conexao`
      confirmou acesso à API pra conta `332-316-6484` ("nenhuma campanha ativa encontrada — conexao
      OK", esperado pra conta nova ainda sem campanhas)
- [ ] Ajustar os placeholders "(AJUSTAR)" no `CLAUDE.md` do `agente-ads` com os dados reais do Integra Foods
- [ ] Rodar `--dry-run` por 2 semanas antes de liberar `--executar` de verdade
- [ ] Depois de validado no Integra Foods, decidir o que fazer com as 2 contas Adoro existentes, e
      replicar (credenciais + guardrails) para 3G Foods

## 5. Multi-site: skill de onboarding + teste com 3G Foods

Os 4 módulos agora suportam multi-site via variável `SITE` — `SITE=<slug> python main.py --auditar`
carrega `.env.<slug>` (em vez de `.env`) e grava em `data/<slug>/`. Sem `SITE`, continua funcionando
pro Integra Foods como antes (compatibilidade). Ver `.claude/skills/onboard-site/SKILL.md` pro
processo completo — criada com a `skill-creator` a partir do padrão que vínhamos repetindo pro
Integra Foods.

**Teste real: onboarding da 3G Foods (22/07/2026)**, usando os IDs que o usuário já tinha
(`GTM-PNBB7STW`, GA4 `514973832`, Ads `758-019-9564`, Search Console `loja.3gfoods.com.br`):

- **Descoberta importante:** os refresh tokens OAuth gerados pro Integra Foods (GTM/GA4/Search
  Console/Ads) **funcionaram direto pra 3G Foods, sem gerar token novo** — o token é por
  conta+escopo, não por site/propriedade. Isso torna o onboarding de um site novo bem mais rápido
  quando é a mesma conta Google administrando tudo.
- **GTM:** 3 tags, 11 triggers, 16 variáveis, tudo publicado. **Achado real:** a tag "Google tag"
  chamada "MERCADO" aponta pra `GT-PZMTMNKK` (formato unificado novo), não pro measurement ID
  `G-7CQV85CBHN` esperado — pode ser container "Google tag" unificado roteando pro GA4 por trás
  (não necessariamente erro), mas fica registrado como divergência pra investigar, não resolvido
  sozinho.
- **GA4:** funil saudável (6205 page_view → 218 view_item → 7 add_to_cart → 5 begin_checkout → 1
  purchase, últimos 7 dias). **Observação:** 18 eventos marcados como conversão (vs. 3 no Integra
  Foods), incluindo `page_view`/`session_start`/`user_engagement` — pode diluir o sinal de conversão
  pro smart bidding do Ads; vale revisar com o usuário, não é um "erro" per se.

**Investigação de tracking de conversões (22/07/2026)**, a pedido registrado em
`agente-julio/pedidos-futuros.md` (11:44 — "validar e configurar rastreamento de conversões GA4 e
Ads"). Feita a parte de leitura/diagnóstico (não simulei uma compra de teste real no site em
produção — criaria pedido de verdade no sistema de fulfillment, risco desproporcional só pra validar
tracking):

- **GA4 confirma dado real no funil**: purchase/add_to_cart/begin_checkout têm volume real nos
  últimos 7 dias (2 compras, 9 add_to_cart, 5 begin_checkout) — tracking de ecommerce está
  funcionando, não é só configuração vazia.
- **GA4↔Ads: 2 contas linkadas, não 1.** `properties.googleAdsLinks.list` mostra a conta esperada
  (`7580199564` = 758-019-9564, "3G Foods", criada por `3gfoodsdigital@gmail.com`) **e uma segunda
  conta desconhecida** (`7466004393`, criada em 2026-01-07 por `eduardo.rezende@integrafoods.ind.br`)
  — não é nenhuma das 3 contas que o projeto usa (Integra Foods V2, 3G Foods, Adoro). Não
  investigado a fundo — pode ser vínculo órfão de teste, mas precisa confirmação humana antes de
  mexer (desvincular uma conta Ads afeta importação de conversão).
- **Google Ads — achado grave, config incorreta confirmada:** a ação de conversão nomeada
  **"Adicionar ao carrinho (Evento do Google Analytics remove_from_cart)"** está de fato configurada
  pra contar o evento `remove_from_cart` — ou seja, **tirar item do carrinho está sendo registrado
  como "adicionar ao carrinho"**. Está `ENABLED` mas felizmente `include_in_conversions_metric=False`
  (não conta pra lance ainda) — mesmo assim é dado errado se alguém olhar o relatório de conversões.
- **Confirma a diluição de smart bidding com números exatos:** das ações de conversão com
  `include_in_conversions_metric=True` (contam pra lance automático), 9 são eventos que não deveriam
  ser conversão de negócio (`page_view`, `session_start`, `first_visit`, `user_engagement`,
  `product_view`, `view_item`, `login`), ao lado das 4 que fazem sentido (`Compra`, `add_to_cart`,
  `begin_checkout`, `register`/`sign_up`). Isso é o "18 eventos marcados como conversão" acima, agora
  com o detalhe de quais especificamente entram no cálculo de lance.
- **Não feito (decisão do usuário, não threshold técnico):** simular compra de teste ponta a ponta,
  e desativar/corrigir as ações de conversão problemáticas — ambos são ações com efeito real
  (transação de verdade / mudança de sinal de otimização ativa), não executadas sem confirmação.
- **Search Console:** 2 sitemaps, 0 erros/avisos, tráfego orgânico ativo. Última leitura de ambos os
  sitemaps é de janeiro/2026 (~6 meses) — não é erro, mas vale confirmar se o sitemap está sendo
  reenviado quando o catálogo muda.
- **Ads:** conexão confirmada, 1 campanha ativa já rodando (`23700278085`, "Campaign #1") — diferente
  do Integra Foods (conta nova sem campanhas), aqui já tem histórico real pra analisar.
- **Cuidado ao reaplicar o `.gitignore`:** o padrão `.env.*` usado pra ignorar `.env.<site>` também
  bate em `.env.example` — precisa do `!.env.example` explícito pra não parar de versionar o template.

**Ajuste de nomenclatura (22/07/2026):** eliminado o `.env` "sem nome" — até o Integra Foods virou
`.env.integrafoods` explícito (`SITE` default é `integrafoods` em vez de string vazia). Nenhum site
é mais tratado como caso especial.

**Onboarding da Adoro (22/07/2026)**, usando os IDs que o usuário colou no `CLAUDE.md`
(`GTM-W7577965`, GA4 `544418642`, Ads `510-339-3778`, Search Console `loja.adoro.com.br`):

- Refresh tokens reaproveitados de novo, sem gerar nada novo — confirma que não é coincidência do
  3G Foods, é o comportamento normal (token por conta+escopo).
- **GTM:** limpo — 2 tags, 1 trigger, 4 variáveis, tudo publicado, tag GA4 confere exatamente com
  `G-5QBHKPD8BW`. Diferente da 3G Foods, aqui bateu 100%.
- **GA4:** funil muito saudável — 666 page_view → 85 view_item → 62 add_to_cart → 32 begin_checkout
  → 21 purchase (7 dias). "purchase" marcado como conversão.
- **Search Console — achado importante:** `sitemaps: []` (nenhum sitemap enviado) e as 10 principais
  queries orgânicas são todas sobre **uma empresa diferente** ("Ad'oro", fábrica de ração animal em
  São Carlos), todas com **0 cliques**. Contraste com GTM/GA4 mostrando tráfego pago/direto saudável
  (21 compras em 7 dias) — sugere que o SEO da Adoro está praticamente abandonado/nunca trabalhado,
  não é erro de configuração da nossa auditoria. Vale investigar com o usuário antes de agir.
- **Ads:** conexão confirmada (mesmo `GOOGLE_ADS_LOGIN_CUSTOMER_ID` da MCC IF Apoio funcionou, apesar
  de a conta aparecer como item separado no seletor visual do Ads), sem campanhas ativas no momento.

**3 sites onboarded no total agora: integrafoods, 3gfoods, adoro** — todos os 4 módulos rodando
auditoria real pros três.

## Teste real do Julio com o gestor de marketing da 3G Foods (22/07/2026)

Conversa real pelo Telegram (chat_id `8800634507`, "Leandro Falcão" — gestor de marketing, não o
usuário do projeto) enquanto o bot rodava pra validação. Pediu pro Julio atuar como CMO da 3G Foods
e planejar tudo pra gerar vendas. O Julio consultou tráfego real antes de responder (508 sessões,
2 compras, R$4.216,14 em 7 dias — Paid Search puxando a maior parte da receita) e foi coletando
decisões de negócio passo a passo, a pedido do próprio gestor ("me dê um passo a passo... de forma
segmentada").

**Decisões de negócio reais capturadas na conversa** (a campanha nunca chegou a ser confirmada —
bot foi encerrado no meio do fluxo, antes do Julio montar o rascunho final):
- Escopo: **loja inteira**, não uma categoria específica
- Landing page: **homepage** (`https://loja.3gfoods.com.br/`) como padrão
- Orçamento: **R$ 40/dia** — bem abaixo da sugestão do briefing atual (`CLAUDE.3gfoods.md` sugere
  ~R$333/dia com base no orçamento mensal de R$10.000); o gestor quer começar pequeno
- **Geo-targeting: restringir a campanha só pra cidade de São Paulo**

**Achado técnico importante: essa última decisão não é executável hoje.** `campaign_builder.py`
tem `GEO_TARGET_BRASIL` fixo no código (targeting sempre Brasil inteiro) — não existe segmentação
por cidade/estado. O schema `propor_campanha` do `agente-julio/src/orchestrator.py` também não tem
campo de geografia — o Julio nem pergunta isso hoje, então se essa conversa tivesse ido até o fim,
a proposta teria sido criada errada (Brasil inteiro em vez de só São Paulo) sem ninguém perceber até
revisar manualmente no Google Ads. **Bloqueador real pra atender esse pedido específico** — precisa
de decisão de arquitetura (adicionar `geo_target_constant` configurável ao schema + ao
`campaign_builder.py`) antes de qualquer campanha real da 3G Foods ser criada com essa restrição.

Também gerou 2 `pedidos-futuros.md` reais durante a conversa (já registrados e referenciados acima):
validação de tracking (mesmo item já investigado nesta sessão) e criação de 2-3 landing pages de
teste (produto/categoria/oferta) — esse segundo ainda não avaliado.
