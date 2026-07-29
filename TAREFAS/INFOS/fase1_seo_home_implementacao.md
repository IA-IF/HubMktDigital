# Fase 1 — SEO da Home (3G Foods) — implementação pronta pra aplicar

Já apliquei e testei (`npm run build` sem erro, verificado em
`localhost:5173`) essas duas mudanças no repo `c3g-web`. Este arquivo só
documenta o antes/depois pra você aplicar direto, sem precisar caçar no
código.

## Arquivo 1: `src/router/routes.js`

A rota raiz (`path: '/'`, é a URL real `https://loja.3gfoods.com.br/`)
não tinha `meta` nenhum — por isso caía no fallback genérico ("3G Foods"
/ "Excelência na distribuição de alimentos").

**Antes:**
```js
{
    path: '/',
    component: () => import("@/pages/HomePage.vue"),

},
```

**Depois:**
```js
{
    path: '/',
    component: () => import("@/pages/HomePage.vue"),
    meta: {
        title: 'Distribuidora de Alimentos para Food Service em São Paulo | Carnes, Congelados, Laticínios | 3G Foods',
        description: 'Distribuidora de alimentos especializada em food service. Carnes bovinas, aves, suínos, congelados, laticínios, mercearia e muito mais. Entregas em mais de 200 municípios de São Paulo.',
    },
},
```

## Arquivo 2: `src/pages/HomePage.vue`

A página não tinha nenhum `<h1>` (nem escondido, nem visível). Adicionei
um H1 real pra SEO/acessibilidade, mas **visualmente escondido**
(`.visually-hidden`, classe do Bootstrap que já está no projeto) pra não
duplicar visualmente o headline que já vem embutido na imagem do banner.

**Antes** (início do `<template>`):
```html
<main class="main-wrapper">

    <!-- HERO BANNER START -->
```

**Depois:**
```html
<main class="main-wrapper">

    <h1 class="visually-hidden">Distribuidora de Alimentos para Food Service em São Paulo</h1>

    <!-- HERO BANNER START -->
```

## Como validar depois de aplicar

```
npm run build
```
Deve compilar sem erro. Pra conferir visualmente sem quebrar nada, roda
`npm run dev`, abre a home, e no DevTools (F12 → Elements, `Ctrl+F`)
busca por `<h1` — deve aparecer o texto acima, mas a página não muda
visualmente (H1 fica invisível, só existe pro Google/leitor de tela).

## Escopo

Isso cobre só a Fase 1 (SEO) do `TAREFAS/plano_acao_3gfoods_home.md`. A
Fase 2 (barra de confiança, banners 2/3, copy institucional, CTA final)
ainda não tem código — só a ordem das seções já está aprovada, ver o
plano de ação.
