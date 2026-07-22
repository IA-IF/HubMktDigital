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
`C:\INTEGRAFOODS\www\web2\IA\GTM-PJWJJHXR_workspace7.json`. O que falta criar/verificar:

- Acesso à conta Google (via API do GTM) para ler o container direto do Google, não só pelo export local
- Confirmar se a versão publicada (live) bate com o que está nesse export, ou se é só rascunho (workspace)
- Confirmar que a tag GA4 está disparando de verdade no site em produção (o `config.js` só ativa GTM em `PROD`)
- Verificar se a tag de e-commerce cobre o funil todo (view_item, add_to_cart, purchase) com os parâmetros certos

## 2. Google Analytics (GA4)

- (a preencher)

## 3. Search Console

- (a preencher)

## 4. Google Ads

Já temos referência (`C:\INTEGRAFOODS\teste\GADS\agente-cmo`), hoje configurada pra 3G Foods.
Como o laboratório agora é o Integra Foods, o que falta criar:

- Credenciais Google Ads da conta do Integra Foods (o agente hoje só conhece a conta da 3G Foods)
- Ajustar os placeholders "(AJUSTAR)" no `CLAUDE.md` do agente com os dados reais do Integra Foods
- Rodar `--dry-run` por 2 semanas antes de liberar `--executar` de verdade
- Depois de validado no Integra Foods, replicar (credenciais + guardrails) para 3G Foods e Adoro
