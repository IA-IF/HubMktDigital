# Status do projeto (pra explicar pro gestor)

Este arquivo é o contexto fixo que o Julio usa em toda conversa (ver
`orchestrator._sistema`) pra explicar o projeto e saber o que já
funciona de verdade. Escrito em linguagem simples, sem jargão técnico —
é o que o Julio vai explicar pro gestor. Manter atualizado conforme o
projeto avança.

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
## Como pedir uma mudança no próprio projeto

Além de responder sobre marketing (dados reais de tráfego/anúncios) e
sobre dúvidas do projeto, o Julio consegue anotar e já preparar pedidos
de mudança no próprio projeto — coisas como "quero que o bot também
avise sobre X" ou "muda como você responde tal coisa".

Quando isso acontece:
1. O Julio anota o pedido e prepara um rascunho técnico automaticamente
   (pode levar um tempinho).
2. Ele pergunta se quer aplicar aquilo agora.
3. Se a resposta for "sim", ele aplica de verdade — e se algo der
   errado, ele mesmo desfaz e volta pro estado anterior sozinho, sem
   precisar de ninguém mexendo por fora.
4. O gestor pode perguntar a qualquer momento como estão os pedidos que
   já fez.
