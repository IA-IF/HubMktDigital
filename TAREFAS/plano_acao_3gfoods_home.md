# Plano de Ação — Home 3G Foods

Fonte de conteúdo: `TAREFAS/INFOS/Plano_Implementacao_3GFoods_Home.md`
(documento já pronto, entregue pelo Eduardo). Este arquivo só organiza
execução em partes e registra o que falta pra cada parte sair do papel.

## Fase 1 — SEO (Melhoria 6 do documento fonte)

**Pronto pra aplicar agora, sem gap.**

- Title: `Distribuidora de Alimentos para Food Service em São Paulo | Carnes, Congelados, Laticínios | 3G Foods`
- Meta description: `Distribuidora de alimentos especializada em food service. Carnes bovinas, aves, suínos, congelados, laticínios, mercearia e muito mais. Entregas em mais de 200 municípios de São Paulo.`
- H1: `Distribuidora de Alimentos para Food Service em São Paulo`
- H2s sugeridos: Mais de 300 produtos para abastecer seu negócio / Carnes
  Bovinas / Carnes Suínas / Frango / Congelados / Laticínios / Mercearia /
  Marcas Parceiras / Quem Somos / Regiões Atendidas

**Onde aplicar (código já inspecionado):**
- `c3g-web/src/router/routes.js` — adicionar `meta: { title, description }`
  na rota `path: '/'` (linhas 13-17), que hoje não tem nenhuma (causa raiz
  do texto genérico no Google).
- `c3g-web/src/pages/HomePage.vue` — hoje **não tem nenhum `<h1>`**;
  precisa adicionar o H1 acima, mais os H2 de seção onde fizer sentido na
  estrutura atual (carrosséis de "Destaques", "Lançamentos" etc já usam
  `<h2>` pra título de seção — só title-nem os H1 propostos, que
  representam a categoria de negócio, ainda não existem em lugar nenhum).

**Gap:** nenhum.

**Status: EXECUTADO (2026-07-28).**
- `routes.js`: `meta: { title, description }` adicionado na rota `path: '/'`.
- `HomePage.vue`: `<h1 class="visually-hidden">` adicionado (Bootstrap,
  já usado no projeto) com o texto acima — não duplica visualmente o
  banner (que já traz o headline embutido na imagem), só garante que
  Google/leitor de tela enxerguem a página com H1 de verdade.
- `npm run build` rodado em `c3g-web` pra confirmar que compila sem
  erro — build OK. **Ainda não deployado em produção**, aguardando
  autorização.

## Fase 2 — Redesign completo da Home (Melhorias 1-5, 7-9)

Copy de todas as seções (headline, subheadline, CTAs, barra de confiança,
copy institucional, CTA final) já está escrito no documento fonte.

**Gaps que impedem implementar direto:**

1. ~~Números precisam de confirmação real com o negócio~~ **RESOLVIDO
   (2026-07-28)** — conferidos contra o site institucional
   `https://www.3gfoods.com.br/` (fonte de confiança indicada pelo
   Eduardo, não o `ceps_atendidos_3g.json`, marcado incorreto). Os 5
   números batem exatamente:
   - "+300 produtos" ✓ ("portfólio de mais de 300 produtos")
   - "+15.000 clientes" ✓ ("mais de 15 mil clientes ativos")
   - "+2 mil toneladas/mês" ✓ ("mais de 2 mil toneladas distribuídas por mês")
   - "+200 municípios" ✓ ("mais de 200 municípios do estado de SP")
   - "+1.400 pontos de entrega" ✓ ("mais de 1.400 pontos de entrega atendidos diariamente")

2. ~~Banners (Melhorias 3, 4, 5) dependem de imagem/design que não existe
   ainda~~ **EM ANDAMENTO (2026-07-28)** — Banner 1 já tem amostra
   pronta (`TAREFAS/INFOS/ChatGPT Image 28 de jul. de 2026, 18_50_28.png`):
   headline "A DISTRIBUIDORA COMPLETA PARA O SEU NEGÓCIO.", barra de
   indicadores (300+ produtos, entregas diárias, 200+ municípios,
   15.000+ clientes) e CTA "COMPRAR AGORA" — tudo consistente com a
   Melhoria 1/2 do documento fonte. Banners 2 e 3 ainda em produção. O
   Eduardo sobe os arquivos direto no backend/CMS quando prontos — sem
   tarefa de código associada a isso.

3. ~~Onde o texto do banner aparece não está definido tecnicamente~~
   **RESOLVIDO** — a amostra do Banner 1 confirma que o texto (headline +
   indicadores + CTA) vem **embutido na própria imagem**, não como
   overlay HTML. O carrossel atual (`carousel-vue-comp`, renderiza só
   `img_desk`/`img_mobile`) já suporta isso sem nenhuma mudança de
   componente.

4. ~~Barra de confiança (Melhoria 7) e CTA final (Melhoria 9) são seções
   novas, sem posição definida~~ **RESOLVIDO (2026-07-28) — Eduardo
   aprovou a ordem sugerida abaixo.**

**Ordem proposta e aprovada pra Fase 2** (de cima pra baixo na página):

1. Hero banner (já existe — carrossel `banner1`)
2. Barra de confiança (Melhoria 7 — 🚚 Entrega diária, 🥩 300+ produtos,
   📍 200 municípios, 👨🏻‍🍳 15.000 clientes, ❄️ Logística refrigerada) —
   logo abaixo do banner, é o próprio documento fonte que recomenda essa
   posição
3. Carrosséis de produto já existentes (Destaques, Lançamentos etc. —
   sem mudança)
4. Banner 2 (Melhoria 4 — motorista descarregando, "Entregamos todos os
   dias para mais de 1.400 pontos")
5. Banner 3 (Melhoria 5 — prova social, "Mais de 15.000 clientes já
   confiam na 3G Foods")
6. Copy institucional (Melhoria 8 — texto "Há mais de 10 anos...")
7. CTA final (Melhoria 9 — "Pronto para comprar melhor?") — última
   seção antes do rodapé

**Status:** Fase 1 executada (ver acima), aguardando deploy. Fase 2:
todos os gaps de conteúdo/ordem resolvidos — falta só banners 2/3
terminarem de ser produzidos (fora do nosso escopo de código) antes de
implementar as seções novas.
