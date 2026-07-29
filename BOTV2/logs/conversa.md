eduardo: ola

ia: Oi! Bot telegram_v2 funcionando no grupo.

ia: Esse é o canal telegram_v2, pra gente falar nós 3: Eduardo, Leandro e eu (Claude, rodando local no PC do Eduardo).

ia: Criei TAREFAS/CLAUDE.md no projeto -- registro de config/comportamento do telegram_v2 (quem somos os 3, onde ficam os arquivos do BOTV2, como eu leio e respondo aqui). É pra eu não precisar reanalisar o projeto do zero toda vez que a gente continuar essa conversa numa sessão nova.

ia: Criei TAREFAS/integrafoods_tasks.md -- arquivo de controle das tarefas da Integrafoods. Já registrei a primeira: a correção de indexação (402 URLs descobertas, 0 indexadas -- causa era URLs antigas .php quebradas coexistindo com as novas /produto/slug) via redirects 301 + ajuste no robots.txt, já deployado em produção.

ia: Registrei em TAREFAS/integrafoods_tasks.md o plano da auditoria de SEO: 6 paginas alvo (home, categorias, 1 categoria, 3 produtos -- URLs reais tiradas do sitemap), spec com 4 blocos por pagina (on-page, dados estruturados/schema, tecnico via browser, indexabilidade) e um checklist de execucao. Ainda nao executei nada -- vou come\u00e7ar a rodar agora e reporto os achados aqui.

ia: 3G Foods: achei a causa raiz do texto fraco na busca do Google -- routes.js tem 2 rotas pra home, a URL real (/) nao tem meta title/description (cai no fallback generico), a outra rota (/home, que ninguem acessa) tem um texto bom esquecido la. Antes de aplicar o fix, vamos criar um skill de copy SEO pra gerar titles/descriptions fortes e consistentes (temos varias paginas/sites pela frente, nao so essa). Registrado em TAREFAS/3gfoods_tasks.md.

ia: Leandro, preciso da sua ajuda pra escrever bons textos de SEO (title/description) pra 3G Foods -- vou usar isso em varias paginas do site, entao quero acertar a voz antes de comecar. Pelo que vi no catalogo, parece B2B/atacado de alimentos congelados (atende chefs, restaurantes, acougues) -- pode confirmar e me contar: 1) qual e o principal diferencial que a 3G Foods quer que apareca sempre (ex: entrega rapida, preco de atacado, variedade de cortes, qualidade)? 2) tem alguma palavra ou tom que NAO pode faltar (ou que deve ser evitado)? 3) o publico e so B2B mesmo, ou tambem vende pro consumidor final?

ia: 3G Foods -- Fase 1 (SEO da home) executada: meta title/description na rota / e H1 acessivel adicionados (routes.js + HomePage.vue), build testado sem erro. Ainda NAO deployado em producao, aguardando ok. Tambem fechei a ordem da Fase 2 (banner -> barra de confianca -> produtos -> banner2 -> banner3 -> copy institucional -> CTA final), registrada em TAREFAS/plano_acao_3gfoods_home.md. So falta os banners 2/3 terminarem de ficar prontos.

