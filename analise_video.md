# Automatizando Google Ads com Claude Code
*Baseado na transcrição completa do vídeo "Claude Code Google Ads: Automate Everything ($730K Earned)" — Jono Catliff*

## Ideia central

O criador gerou US$730K em Google Ads usando uma estratégia de **SKAGs (Single Keyword Ad Groups)** — um grupo de anúncios por palavra-chave — e agora automatiza literalmente todo o processo (pesquisa de palavras-chave, campanhas, anúncios, landing pages, tracking, auditoria de conta) usando o Claude Code como um "especialista em Google Ads" particular.

Princípio-chave repetido no vídeo: **a busca precisa bater com o anúncio, que precisa bater com a landing page** (e depois com o e-mail e a ligação de vendas). Tudo genérico = resultado ruim.

---

## 0. Ferramentas necessárias

- **VS Code** (gratuito) — onde o Claude Code roda como extensão.
- **Extensão Claude Code** dentro do VS Code.
- Conta **Google Ads** (gratuita) + conta **Google Ads Manager (MCC)**.
- Conta **Google Cloud Console** (gratuita).
- Depois, para publicar: conta **GitHub** e conta **Vercel** (ambas gratuitas).

Crie uma pasta de projeto (ex: `Google Ads`) dentro do seu diretório de apps do Claude Code. Dentro dela, crie dois arquivos base:
- `prompts.md` — todos os prompts que você vai reutilizar
- `setup.md` — o guia passo a passo de conexão (descrito abaixo)

---

## 1. Conectar o Claude Code à sua conta do Google Ads (feito uma única vez)

Primeiro prompt no Claude Code:
> "Please read this setup [setup.md] and connect my account to Google Ads."

O Claude Code cria um arquivo `.env` para guardar as chaves/senhas com segurança. Os passos manuais que você precisa fazer em paralelo:

1. **Criar uma conta Google Ads** normal (gratuita), se ainda não tiver.
2. **Criar uma conta Google Ads Manager (MCC)** — busque "Google Ads Manager account" no Google.
   - Dentro da conta manager: **Contas > Subcontas > Adicionar** e vincule pelo ID da sua conta Google Ads existente.
   - Confirme por e-mail o pedido de vínculo.
3. **Pegar o Developer Token**: dentro da conta manager, vá em **Admin > API Center**. Esse token dá acesso a 2.880 requisições/dia; para mais, é preciso solicitar "Basic Access" (aprovação em ~72h pelo Google).
4. **Google Cloud Console**:
   - Criar um novo projeto (canto superior esquerdo → "Create a new project"), anexar uma conta de faturamento.
   - Entrar no projeto e habilitar a **Google Ads API** (buscar "Google Ads API" → primeiro link → Enable).
   - Ir em **APIs & Services > OAuth consent screen** → "Get Started" → nomear o app (ex: "claude code") → escolher e-mail de suporte → tipo **External** → mesmo e-mail → aceitar termos → criar.
   - Voltar em **OAuth consent screen > Audience** → adicionar seu e-mail como **test user**.
   - Ir em **APIs & Services > Credentials** → **Create Credential > OAuth client ID** → tipo **Desktop application** → criar e **baixar o JSON**.
5. Renomear o arquivo baixado para `credentials.json` e colocar na pasta do projeto.
6. No Claude Code:
   > "I've added in the file credentials.json. Please read it and authenticate me with Google."
   - Vai abrir o navegador pedindo login — use o mesmo e-mail cadastrado como test user, confirme, e pronto: conexão feita permanentemente.

---

## 2. Estrutura: Campanhas > Grupos de anúncios > Anúncios

Pense como pastas aninhadas (tipo Google Drive):
- **Campanha** = agrupa por serviço (ex: "Encanamento de emergência"). Configura orçamento diário, dias/horários, localização.
- **Ad Group (SKAG)** = **uma única palavra-chave por grupo** (ex: só "emergency plumbing Mississauga"). Isso faz o anúncio e a landing page serem hiper-específicos → mais conversão.
- **Ads** = múltiplas variações dentro do grupo para fazer **split testing** — o objetivo é achar 1 anúncio "outlier" campeão e rodar com ele por anos.

### Prompt para criar a primeira campanha
No Claude Code, cole o blueprint `campaigns.md` (arquivo de referência com as regras de configuração) e use:
> "Read the campaigns.md file that we just copied in and build me my very first Google Ads campaign." + seu domínio

O Claude pesquisa sobre sua empresa a partir do domínio e aplica isso à campanha automaticamente. Ele configura:
- **Tipo: Search** (não Performance Max, Display, Demand Gen, Vídeo ou Shopping — o autor considera esses "tráfego de garagem/lixo" para negócios de serviço local).
- **Bid strategy**: começar em "Maximizar conversões"; depois migrar para otimizar por **ROAS real** assim que houver dados de vendas.
- **Localização**: raio de ~50km do centro da cidade-alvo, opção **"Presence" (não "Interest")** — evita mostrar anúncios para quem só está "interessado" na cidade mas mora longe (ex: alguém na Índia interessado em Toronto).
- **Excluded locations**: excluir todos os outros países fora do seu (evita cliques de bot/VPN).
- **Segmentação de audiência**: manter desligada para tráfego frio (não restringir quem vê o anúncio).
- Recomendações automáticas do Google: desligadas (elas existem para você gastar mais, não para performar melhor).

---

## 3. Bid Strategy e como baratear o CPC

Três fatores que reduzem custo por clique:
1. **Smart bidding** — dar tempo para a conta "esquentar" (Google aprende seu público).
2. **Não ranquear para termos de busca ruins** — resolvido em grande parte pela estrutura SKAG (1 anúncio = 1 termo).
3. **Quality Score** alto, que depende de:
   - CTR esperado (quanto maior, mais barato);
   - Relevância do anúncio para o termo (a estrutura SKAG resolve isso);
   - Relevância da landing page para o termo buscado.

---

## 4. Geração em massa de anúncios (RSAs)

Antes de gerar os anúncios, crie dois arquivos de referência (blueprints) que o autor disponibiliza:
- `anatomy-of-a-good-google-ad.md`
- `ad-assets-best-practices.md`

Depois, use o prompt principal para gerar os anúncios. O Claude cria automaticamente:
- 15 headlines + descrições
- **Headlines fixados (pinned)** na posição 1 — sempre a palavra-chave/termo de busca exata, para o usuário reconhecer imediatamente que o anúncio responde à busca dele. As demais headlines (ofertas, diferenciais) ficam livres para o Google rotacionar.
- Sitelinks, structured snippets e callouts (ex: "24/7 emergency service", "no callout fee", "licensed and insured") — servem para **ocupar mais espaço visual no resultado de busca**, aumentando o CTR.
- Opcionalmente: nome da empresa, logo, imagens (cuidado: imagens de baixa qualidade podem reduzir a confiança e o CTR).

> Dica do autor: teste dezenas ou centenas de variações — só é preciso 1 vencedora ("outlier") para multiplicar a conversão. Mas é preciso volume de busca suficiente para o teste ser estatisticamente válido.

---

## 5. Palavras-chave negativas (2 camadas)

**Camada 1 — Lista universal** (genérica, reaproveitável entre campanhas):
- Termos como "plumber school", "plumbing course", "DIY", "job", "coupon", "crypto", "definition" etc. — qualquer coisa que sinalize pesquisa de emprego, educação, DIY ou não relacionada a contratar o serviço.
- Prompt: colar o blueprint `universal-negative-keywords.md` e pedir ao Claude para aplicar essa lista à campanha (ela pode ser compartilhada entre todas as campanhas).

**Camada 2 — Mineração de termos de busca reais** (específica da conta, recorrente):
- Prompt (blueprint `find-and-add-negatives.md`): peça ao Claude para analisar os termos de busca reais que geraram cliques e identificar quais são "lixo" — ex: "DJ hiring" (na verdade gente procurando emprego, não contratando), ou geografias erradas (cliques de uma cidade que a campanha nem deveria alcançar).
- O Claude pode pesquisar na web para confirmar a intenção real por trás do termo antes de recomendar a negativação.
- Você aprova o relatório e o Claude aplica as negativações automaticamente.

---

## 6. Landing pages

Prompt principal: pedir ao Claude para construir a landing page usando o framework **Next.js** (o autor compara a "WordPress para código customizado").

Regra de ouro: **o headline da landing page deve repetir o mesmo termo de busca do anúncio.**

Truque de design: pegue uma referência visual no **Dribbble** (buscar ex: "plumbing website"), salve a imagem e anexe ao prompt do Claude — ele recria o estilo/branding.

Elementos essenciais de uma landing page de alta conversão (segundo o autor, que teve ~20% de conversão):
- **Split testing** contínuo — é o único jeito de saber com certeza o que funciona.
- **Depoimentos em vídeo** (prova social é o fator #1).
- **Formulário na própria página principal** (nunca em página secundária).
- **Vídeo do fundador** — o objetivo não é vender o serviço, é vender *você* (por que escolher você e não o concorrente).
- **"Speed to lead"**: ligar para o lead em até 60 segundos após o preenchimento do formulário (a média do mercado é 48h — só isso pode multiplicar por 4 a taxa de fechamento).
- Boa oferta na página.

> Nota: enquanto não faz o deploy (seção 9), o site roda em localhost e só você consegue ver — não dá pra apontar o Final URL do anúncio pra ele ainda.

---

## 7. Tracking, remarketing e ROAS real

### 7.1 Tag de remarketing
Prompt (blueprint `setup-conversion-tracking-and-audience.md`) + seu domínio real. O Claude instala a **Google Tag** no site e cria uma **audiência** de "qualquer um que já visitou o site".

Para validar se a tag está ativa:
- Use o **Google Tag Assistant** (adicionar o domínio/localhost, testar um evento de envio de formulário).
- Opcional: instalar o plugin **Playwright** do Claude para ele mesmo testar automaticamente no navegador.
- Ou simplesmente cole o relatório do Tag Assistant no Claude e pergunte: "Can you tell me if the remarketing tag is set up properly via the Google Tag Assistant?"

### 7.2 Público frio vs. quente
- **Frio**: nunca viu sua marca — tudo que foi montado até aqui.
- **Quente/remarketing**: já visitou o site. Recomendação do autor: priorizar **RLSA (remarketing em Search)** — mesmos anúncios de busca, mas para quem já visitou o site (custo maior, conversão maior). Remarketing em **Display** é "hit or miss" — só vale tentar, sem garantias.

### 7.3 ROAS real (o pipeline completo)
1. **Parâmetros de URL** no link do anúncio (`?keyword=...&campaign=...&gclid=...&utm_source=google&utm_medium=cpc`).
2. **Campos ocultos no formulário** capturam esses parâmetros da URL.
3. Ao enviar o formulário, esses dados (incluindo o `gclid`) vão para o **CRM** junto com o lead.
4. Quando o cliente efetivamente **paga**, você atualiza o CRM e exporta esses dados (nome, valor pago, `gclid` etc.) como **CSV**.
5. **Importa esse CSV de volta no Google Ads** ("offline conversion import") — assim o Google aprende quais cliques viraram clientes pagantes de verdade (e quanto pagaram), e passa a otimizar a entrega dos anúncios para esse perfil de conversão real — não apenas "gerou lead".

> O autor reforça: esse pipeline muda de negócio para negócio (depende do seu CRM), mas o Claude Code pode te ajudar a montar cada uma dessas 5 etapas em conversa.

---

## 8. Dashboard de auditoria/analytics

Prompt principal para o Claude construir um dashboard simples (MVP) mostrando:
- Ad spend total
- Target CPA
- Campanhas quebradas por spend, revenue e ROAS
- Recomendações automáticas: quais campanhas pausar, quais escalar o orçamento, quais keywords remover/corrigir

Você também pode pular o dashboard e simplesmente pedir diretamente ao Claude, periodicamente:
> "Pode auditar minha conta e me dizer o que corrigir para ficar mais rentável?"

---

## 9. Publicar o site (deploy)

Processo em duas etapas, ambas gratuitas:

1. **GitHub**
   - Criar conta → Repositories → New → marcar como **Private** → Create.
   - Copiar o comando/URL do repositório gerado.
   - No Claude Code: "Please upload my entire website to this [URL]. The folder is landing-pages." (especifique a pasta certa para não subir arquivos markdown/scripts desnecessários).

2. **Vercel**
   - Criar conta → New Project → conectar com GitHub → importar o repositório criado.
   - Garantir que o preset da aplicação está como **Next.js**.
   - Deploy.

Depois do deploy, o domínio gerado pela Vercel costuma ser feio — você pode comprar um domínio direto pela Vercel ou usar um provedor externo (GoDaddy, Namecheap).

**Passo final obrigatório**: voltar nas campanhas do Google Ads e trocar o **Final URL** de cada anúncio (que estava apontando pra homepage como placeholder) para a landing page específica recém-publicada daquele grupo de anúncios.

---

## 10. Criar uma "Skill" no Claude Code para repetir o processo em segundos

Depois de montado tudo uma vez, o gargalo é repetir o processo manualmente toda vez. A solução é criar uma **Skill** (workflow sob demanda) no Claude Code:

1. Copie o prompt de criação de skill (blueprint da comunidade) no Claude Code.
2. Isso gera um arquivo de skill que fica na estrutura de arquivos do projeto (ex: acessível via `/generate-ads`).
3. Uso no dia a dia: abra uma nova conversa e digite `/generate-ads` (ou o nome que você deu à skill) + um contexto curto, por exemplo:
   > "/generate-ads please generate another five ads in the Toronto plumbing ad group."
4. O Claude executa sem precisar reexplicar todo o contexto/regras de novo.

---

## Checklist rápido de implementação

- [ ] VS Code + extensão Claude Code instalados
- [ ] Conta Google Ads + conta Manager (MCC) criadas e vinculadas
- [ ] Developer Token obtido no API Center
- [ ] Projeto no Google Cloud + Google Ads API habilitada
- [ ] OAuth consent screen configurado + test user adicionado
- [ ] `credentials.json` gerado e autenticado no Claude Code
- [ ] Primeira campanha Search criada (SKAG) com localização por "Presence" e países excluídos
- [ ] Lista de negative keywords universal aplicada
- [ ] Anúncios RSA gerados em massa (headline pinado = termo de busca exato)
- [ ] Mineração de negative keywords a partir de termos de busca reais (recorrente)
- [ ] Landing page criada (headline = termo de busca, prova social, formulário na página principal, vídeo do fundador, speed-to-lead)
- [ ] Google Tag de remarketing instalada e validada (Tag Assistant)
- [ ] Audiência de remarketing configurada (priorizar RLSA)
- [ ] Pipeline de ROAS real montado (parâmetros de URL → campos ocultos → CRM → CSV → import no Google Ads)
- [ ] Dashboard/auditoria de conta configurado
- [ ] Site publicado (GitHub + Vercel) e Final URLs atualizadas nos anúncios
- [ ] Skill criada no Claude Code para repetir o processo (`/generate-ads` etc.)

---
*Fonte: transcrição integral do vídeo "Claude Code Google Ads: Automate Everything ($730K Earned)" (canal Jono Catliff). https://www.youtube.com/watch?v=-EInjdpjKy0*
