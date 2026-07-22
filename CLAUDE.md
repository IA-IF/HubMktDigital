Preciso criar um AGENT de IA , especializado em marketing digital

trabalho com desenvolvimento, e gestao de ecommerce, no segmeto de proteina e alimentos (carnes)

tenho 3 sites no momento que precisam de ações de campanhas pagas, 
sao esses 

https://integrafoods.ind.br/
codigo: "C:\INTEGRAFOODS\www\web2"


https://loja.3gfoods.com.br/
codigo: "C:\INTEGRAFOODS\www\c3g-web"



https://webadoro.conge.digital/
codigo: "C:\INTEGRAFOODS\www\adoro-web"



não é interessante analizar o codigo desses projetos no momento, mas no futuro vamos ter q fazer isso 


agora quero focar em


Quero usar o google ads
com gtm
e com analitcs

nessa pasta "C:\INTEGRAFOODS\teste\GADS" fiz um teste da criação de ua ferramenta, mas ainda nao esta madura  o suficiente
(essa pasta vale a pena analizar)


Eu queria um agente que fosse capaz de acessar as contas , verificar , e propor , e ate alterar , de acordo com a necessidade

por exemplo, o gtm esta bem configurado
o analitcs tem as configurações para registrar o track do site
o ads tem as converssoes corretas , etc


quero q vc materializa em um brainstorm.md , algumas ideias para construir esse agente





3g

gtm 
GTM-PNBB7STW

analitcs
ID DA PROPRIEDADE: 514973832 

ads
3G Foods
758-019-9564

searchconsole
https://search.google.com/search-console?resource_id=https%3A%2F%2Floja.3gfoods.com.br%2F







adoro

gtm 
GTM-W7577965

analitcs
ID DA PROPRIEDADE: 544418642 


ads
Loja Adoro
510-339-3778

searchconsole
https://search.google.com/search-console?resource_id=https%3A%2F%2Floja.adoro.com.br%2F


proxima tarefa (feito 2026-07-22): agente-ads agora suporta Anthropic e OpenAI
via LLM_PROVIDER (default "openai", ja que era o credito disponivel). Chaves
reais ficam so nos `.env.<site>` (gitignored), nunca aqui no CLAUDE.md.





desmembrar o agente-julio (feito 2026-07-22): criado ../agente-julio, o
orquestrador que conversa com o humano no Telegram e aciona os outros
agentes via subprocess (main.py --criar-campanha do agente-ads, sem
importar codigo entre modulos). agente-ads perdeu o telegram_bot.py e o
--telegram-bot; so expoe a capacidade de criar campanha. Chaves reais
(Telegram, LLM) ficam so nos `.env.<site>` (gitignored), nunca aqui.




skills de ga4 testadas (2026-07-22, pasta skills-teste/ isolada, depois
apagada): jdrhyne/agent-skills:ga4 (CLI generico de consulta, sem
site-selection nem anti-alucinacao — nosso agente-ga4/src/trafego.py +
agente-julio ja cobre isso melhor pro nosso caso), cognyai/claude-code-
marketing-skills:ga4-measurement-plan (desenha plano de tracking a partir
do site, nao consulta dado real — util pra outra tarefa, nao pra agora),
:ga4-bigquery-schema (referencia de SQL, nao se aplica — nenhum site tem
export pro BigQuery configurado). Nenhuma virou dependencia do projeto.