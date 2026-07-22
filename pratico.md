# Prático

Sites:

- https://integrafoods.ind.br/ — `C:\INTEGRAFOODS\www\web2` — **laboratório, começamos por aqui**
- https://loja.3gfoods.com.br/ — `C:\INTEGRAFOODS\www\c3g-web` — depois, replicando o que funcionar no Integra Foods
- https://webadoro.conge.digital/ — `C:\INTEGRAFOODS\www\adoro-web` — depois, replicando o que funcionar no Integra Foods

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
- **Search Console:** 2 sitemaps, 0 erros/avisos, tráfego orgânico ativo. Última leitura de ambos os
  sitemaps é de janeiro/2026 (~6 meses) — não é erro, mas vale confirmar se o sitemap está sendo
  reenviado quando o catálogo muda.
- **Ads:** conexão confirmada, 1 campanha ativa já rodando (`23700278085`, "Campaign #1") — diferente
  do Integra Foods (conta nova sem campanhas), aqui já tem histórico real pra analisar.
- **Cuidado ao reaplicar o `.gitignore`:** o padrão `.env.*` usado pra ignorar `.env.<site>` também
  bate em `.env.example` — precisa do `!.env.example` explícito pra não parar de versionar o template.
