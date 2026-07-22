---
name: onboard-site
description: >
  Conecta um site/marca novo aos quatro auditores deste projeto
  (agente-gtm, agente-ga4, agente-search-console, agente-ads) — GTM, GA4,
  Search Console e Google Ads. Use sempre que o usuário der os IDs de
  plataforma de um site (container GTM tipo GTM-XXXXXXX, property ID
  numérico do GA4, customer ID do Google Ads, URL do Search Console) e
  pedir para configurar, conectar, adicionar, integrar ou "criar" esse
  site no sistema — mesmo que ele não diga a palavra "onboarding" ou
  "skill". Também dispara em pedidos como "configura a conta X aqui",
  "bota o site Y pra rodar auditoria" ou quando o usuário cola uma lista
  de IDs de GTM/GA4/Ads/Search Console de um site que ainda não está no
  `pratico.md`.
---

# Onboard de site novo

Este projeto (`C:\INTEGRAFOODS\teste\HubMktDigital`) audita GTM, GA4, Search
Console e Google Ads de vários sites/marcas da mesma empresa. O Integra
Foods foi o primeiro (laboratório); esta skill captura o padrão que
descobrimos fazendo aquele processo manualmente, para repetir em qualquer
site novo sem reinventar a arquitetura a cada vez.

## Por que multi-site funciona assim

Os quatro módulos (`agente-gtm`, `agente-ga4`, `agente-search-console`,
`agente-ads`) são código genérico — nenhuma linha Python é específica de um
site. O que muda por site é só o `.env.<slug>`. Por isso cada módulo aceita
uma variável de ambiente `SITE`: `config.py` sempre carrega `.env.<SITE>`
(nunca um `.env` sem nome — mesmo o Integra Foods, o site original, é
`.env.integrafoods`; sem `SITE` definido o padrão cai em `integrafoods`,
não num arquivo especial). Dados de cada auditoria vão pra `data/<SITE>/`.
Isso evita duplicar os ~9 arquivos Python de cada agente a cada site novo —
só se duplica configuração, nunca lógica.

**Não crie pastas `agente-gtm-<site>/` novas.** Isso reintroduz o problema
que essa arquitetura resolve. Sempre passe `SITE=<slug>` para o módulo
existente.

## O fluxo (5 passos)

### 1. Resolver os IDs de plataforma do site

Você precisa de 4 dados, um por plataforma. Às vezes o usuário já tem todos
(como aconteceu com a 3G Foods); às vezes é preciso caçar no código do site
(foi o caso do Integra Foods — o GTM ID apareceu em `ssr-poc/src/config.js`,
o measurement ID do GA4 na tag exportada do GTM). Se faltar algum, procure
primeiro no repositório do site antes de pedir para o usuário:

| Dado | Formato | Onde geralmente aparece |
|---|---|---|
| Container GTM | `GTM-XXXXXXX` | snippet do GTM no `<head>`/config do site |
| Account ID + Container ID do GTM (numéricos) | `accounts/<N>/containers/<N>` | só aparece navegando tagmanager.google.com, ou em exports `.json` do workspace |
| Property ID do GA4 | número (ex: `514973832`) | painel do GA4, ou variável `GA_PROPERTY_ID` no código |
| Measurement ID do GA4 | `G-XXXXXXXXXX` | tag "Google tag" no GTM, ou `gtag('config', ...)` no código |
| Customer ID do Ads | `NNN-NNN-NNNN` | conta do Google Ads, ou já documentado em `agente-cmo`/`agente-ads` se for outro site da mesma MCC |
| URL do Search Console | `https://dominio/` (URL-prefix) ou `sc-domain:dominio` | dropdown de propriedades em search.google.com/search-console |

**Cuidado com contas/containers legados.** No Integra Foods existiam
containers/propriedades duplicados ou abandonados (ex: `GTM-W6GWZX5` era
legado, `GTM-PJWJJHXR` era o ativo; duas contas Ads da Adoro apareceram sem
o usuário lembrar). Antes de assumir que um ID está certo, confirme com o
usuário se há mais de uma opção — não adivinhe qual é o "certo" sozinho.

### 2. Confirmar acesso (navegador guiado, se necessário)

Se você (ou a conta Google que a automação vai usar) ainda não tem certeza
de ter acesso às 4 propriedades, use o Playwright para navegar até cada
console (`tagmanager.google.com`, `analytics.google.com`,
`search.google.com/search-console`, `ads.google.com`) igual fizemos pro
Integra Foods: você abre o navegador, o humano loga, você navega até
Admin/Gerenciamento de usuários e confere o nível de acesso. Ver
`../../acesso-guiado.md` (na raiz do projeto) para o padrão completo —
inclusive a regra de nunca clicar em ações que concedem acesso sem
confirmar antes com o usuário.

Se o mesmo usuário/conta que já configurou o Integra Foods tem acesso (ex:
mesma MCC do Ads, mesmo Google Workspace), geralmente o acesso já existe —
foi o que aconteceu nos 4 casos do Integra Foods. Vale checar antes de
assumir que precisa pedir acesso novo.

### 3. Gerar o `.env.<slug>` de cada módulo

Para cada um dos 4 módulos, copie o `.env.example` correspondente para
`.env.<slug>` (nunca sobrescreva o `.env.<outro-site>` de um site que já
funciona) e preencha:

- Os 4 IDs resolvidos no passo 1 (um indo em cada módulo)
- `CLIENT_ID`/`CLIENT_SECRET` — normalmente os **mesmos** dos outros sites
  já configurados (mesmo projeto Google Cloud, ex: `agente-cmo-ads-interno`)
  se a mesma organização/MCC administra tudo. Olhe o `.env.<outro-site>` já
  existente no mesmo módulo para confirmar se pode reaproveitar —
  não precisa ler o valor pra copiar, só pedir pro usuário confirmar que é
  o mesmo client, e escrever direto se você já souber o valor de uma sessão
  anterior.
- `REFRESH_TOKEN` fica em branco por enquanto — vem do passo 4.

Nunca tente ler `.env`/`.env.<slug>` de outro módulo/site via `cat`/`grep`
direto — isso costuma ser bloqueado pelo classificador de segurança do
Claude Code (são credenciais). Peça pro usuário colar o valor, ou escreva
direto se já souber o valor de algo que você mesmo gerou nesta sessão.

### 4. Gerar refresh token (se precisar)

Cada módulo já tem um `generate_refresh_token_*.py`. Rode com o site
selecionado:

```
cd agente-gtm && SITE=<slug> python generate_refresh_token_*.py
```

(No Windows PowerShell: `$env:SITE="<slug>"; python generate_refresh_token_*.py`.)

Isso abre o navegador pra reautorizar com o scope daquele módulo — mesmo
reaproveitando o client_id/secret de outro site, o token em si costuma
precisar ser gerado de novo, porque o scope de cada `.env.<slug>` é
específico do site. Copie a saída pro `.env.<slug>`.

### 5. Rodar a primeira auditoria e registrar

```
cd agente-gtm && SITE=<slug> python main.py --auditar
```

Repita para os 4 módulos. Leia o resultado — não assuma que rodou limpo,
mesmo achado (ex: "0 tags sem trigger") vale conferir no JSON de saída.
Depois:

- Registre o resultado no `pratico.md` (mesmo formato usado pro Integra
  Foods: checklist com `[x]`, os IDs encontrados, achados da auditoria)
- Se algo estiver estruturalmente errado (container nunca publicado, tag
  GA4 não bate, sitemap com erro), isso é um achado real do site — não
  conserte sozinho, reporte pro usuário decidir o que fazer.
- Faça um commit local (`git add` + `git commit`) do progresso, seguindo o
  padrão dos commits anteriores deste projeto (mensagem em português,
  explicando o quê e o porquê, sem emojis).

## O que esta skill NÃO faz

- Não cria conta nova em nenhuma plataforma (isso é uma ação administrativa
  real — se o site precisar de uma conta Ads/GA4/GTM/Search Console do
  zero, confirme com o usuário antes, do jeito que fizemos ao criar a
  conta "Integra Foods V2" no Ads).
- Não decide guardrails de negócio (ROAS mínimo, teto de gasto) — isso é o
  `CLAUDE.<slug>.md` do `agente-ads`, preenchido com dados reais do
  negócio, nunca inventado.
- Não publica nada no GTM nem executa ações no Ads — os 4 módulos aqui são
  só auditoria (leitura). Execução de mudanças é outro fluxo, com
  guardrails próprios (ver `agente-ads/CLAUDE.md`).
