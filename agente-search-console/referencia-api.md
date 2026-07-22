# Referência — o que a API do Search Console oferece (e o que a gente usa hoje)

Mesmo processo dos outros dois (`agente-ga4`, `agente-gtm`): levantado do
discovery document ao vivo em 2026-07-22. Essa é de longe a **menor** das
3 APIs — só 11 métodos ao todo — então o recorte curado é praticamente o
catálogo inteiro.

## Biblioteca e autenticação

Igual aos outros: `google-api-python-client` + `google-auth`, scope hoje
`https://www.googleapis.com/auth/webmasters.readonly` (só leitura).

## O que `search_console_auditor.py` usa hoje (2 de 11 métodos)

```python
service.sitemaps().list(siteUrl=site_url)
service.searchanalytics().query(siteUrl=site_url, body={...})
```

## Catálogo completo

| Método | Requer | O que traz |
|---|---|---|
| `searchanalytics.query` | `siteUrl` + body (`startDate`, `endDate`, `dimensions[]`) | **Já usado** — o único método de dado real da API. Aceita `dimensions`: `DATE, QUERY, PAGE, COUNTRY, DEVICE, SEARCH_APPEARANCE, HOUR`; e `searchType`: `WEB, IMAGE, VIDEO, NEWS, DISCOVER, GOOGLE_NEWS`. Hoje só usamos `dimensions=[QUERY]`; cortar por `PAGE` ou `DEVICE` também é trivial — mesma chamada, dimension diferente |
| `sitemaps.list` | `siteUrl` | **Já usado** |
| `sitemaps.get` | `siteUrl`, `feedpath` | Detalhe de 1 sitemap especifico (o `.list` já traz os campos que usamos, get só é útil se quisermos aprofundar num sitemap específico) |
| `sitemaps.submit` | `siteUrl`, `feedpath` | **Escrita** — submete um sitemap novo. Achado do `pratico.md` (Adoro com 0 sitemaps) poderia virar ação aqui, mas é decisão separada (efeito real na indexação do site) |
| `sitemaps.delete` | `siteUrl`, `feedpath` | **Escrita** — remove um sitemap da lista (não impede o Google de já ter rastreado as URLs) |
| `sites.list` | — | Lista as propriedades que a conta autenticada enxerga no Search Console — **rejeitado como fonte de auto-descoberta**, mesma regra dos outros 2 (site sempre por seleção explícita) |
| `sites.get` | `siteUrl` | Confirma nível de permissão (`siteOwner`, `siteFullUser`, etc.) na propriedade |
| `sites.add` / `sites.delete` | `siteUrl` | **Escrita** — adiciona/remove uma propriedade da conta. Fora de escopo, decisão administrativa rara |
| `urlInspection.index.inspect` | body (URL + siteUrl) | **Candidato forte pra tool nova**: inspeciona o status de indexação de uma URL específica (indexada? bloqueada por robots.txt? tem erro de cobertura?) — não coberto pelo auditor hoje, e é justamente o tipo de pergunta que alguém faria ("por que essa página não aparece no Google?") |
| `urlTestingTools.mobileFriendlyTest.run` | body (URL) | Teste de mobile-friendliness de uma URL — dado isolado, baixo valor pra conversa recorrente |

## Achado à parte

`sitemaps.submit` existe e é simples de chamar — o achado já documentado no
`pratico.md` (Adoro com `sitemaps: []`, zero sitemap enviado) tem uma
correção técnica direta disponível na API. Ainda assim é uma ação que
afeta indexação real do site; não implementar sem decidir antes o mesmo
tipo de guardrail que a Ads tem (nesse caso, provavelmente: sempre pedir
confirmação humana, nunca rodar sozinho).

## Próximo passo natural

Um tool `consultar_search_console` nos moldes do `consultar_trafego`
cobriria: status de sitemaps + top queries dos últimos 28 dias (o que o
auditor já faz) — e `urlInspection.index.inspect` é o candidato natural
pra uma segunda tool, específica pra "por que essa URL não indexa".
