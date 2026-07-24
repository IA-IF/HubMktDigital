# Status do projeto (pra explicar pro gestor)

Este arquivo é o que o Julio usa como contexto quando o bot está em
"modo projeto" (`MODO_PROJETO=1`). Escrito em linguagem simples, sem
jargão técnico — é o que o Julio vai explicar pro gestor. Manter
atualizado conforme o projeto avança.

## O que é o projeto

Um agente de inteligência artificial (o "Julio") pra cuidar do
marketing digital de 3 lojas virtuais de proteína/alimentos: Integra
Foods, 3G Foods e Adoro. A ideia final é o Julio conseguir olhar os
dados reais de cada loja (visitas, vendas, anúncios) e ajudar a tomar
decisões — hoje, principalmente, respondendo perguntas com dados reais
e propondo campanhas novas de anúncio no Google.

## O que já funciona de verdade hoje

Quando o modo normal está ligado (fora do modo projeto), o Julio
consegue, com dados reais (não inventados, não de exemplo):

- Mostrar como está o tráfego e as vendas do site (Google Analytics)
- Mostrar como estão os anúncios pagos — quanto custou, quantas vendas
  vieram deles (Google Ads)
- Mostrar como está o site nas buscas do Google (Search Console) —
  cliques, posição, se o Google está indexando as páginas certas
- Ler a lista de produtos que a loja vende (direto do site)
- Montar uma campanha de anúncio nova completa (nome, orçamento, lance,
  palavras-chave, textos) — sempre pausada, sempre pedindo confirmação
  antes de criar de verdade, ninguém coloca no ar sem revisar

Tudo isso funciona pros 3 sites, cada um com suas próprias regras de
negócio (público, orçamento, meta de retorno).

## O que ainda está pendente

- **Tag Manager (GTM)**: já temos a documentação de como usar essa
  parte do Google, mas o Julio ainda não sabe fazer nada com ela na
  conversa.
- **Catálogo de produtos da 3G Foods**: o jeito de ler a lista de
  produtos desse site em especial era ruim/desatualizado — precisa
  confirmar se já foi corrigido.
- **Verificar velocidade/qualidade técnica das páginas**: dá pra saber
  se o Google indexou as páginas, mas ainda não dá pra medir se as
  páginas carregam rápido — falta ligar isso a um navegador de
  verdade.
- **O sistema completo ainda não está pronto pra ser usado no dia a
  dia** — por isso o bot está, por enquanto, neste modo de
  apresentação: explicar o que existe e anotar pedidos, em vez de
  tentar rodar tudo antes da hora.

## O que o Julio faz nesse modo (modo projeto)

- Explica o que já existe e o que falta, respondendo dúvidas.
- Quando o gestor descreve algo que quer mudar ou adicionar no
  projeto, o Julio anota o pedido e já deixa um rascunho técnico
  preparado, pra equipe revisar antes de colocar no ar — o Julio
  nunca coloca uma mudança no ar sozinho, sem revisão.
- O gestor pode perguntar a qualquer momento como estão os pedidos que
  já fez.
