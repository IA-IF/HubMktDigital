# SKAG Ads + Negative Keywords — Design

Data: 2026-07-24
Status: aprovado, pronto pra virar plano de implementação
Fonte: análise de `video.md` (transcrição) e `analise_video.md` (resumo
de IA, tratado como não confiável — usado só como índice, toda
afirmação foi conferida contra a transcrição original) do vídeo "Claude
Code Google Ads: Automate Everything ($730K Earned)" (Jono Catliff).

## Contexto

O vídeo descreve um fluxo de automação de Google Ads pra um negócio de
serviço local que **não tem site ainda**: pesquisa de keyword,
estratégia SKAG (Single Keyword Ad Group), geração de anúncios em
massa, negative keywords, criação de landing pages do zero em Next.js,
tracking/remarketing, pipeline de ROAS via CRM, dashboard de auditoria,
e deploy (GitHub + Vercel).

O HubMktDigital atende 3 e-commerces **já existentes** (Integra Foods,
3G Foods, Adoro), com páginas de produto/categoria reais (`TOOLS/CATALOGO/
catalogo_produtos`) e uma tool de criação de campanha já funcional
(`TOOLS/ADWORDS/criar_campanha`). Nem tudo do vídeo se aplica: landing
pages novas e pipeline de CRM não fazem sentido pra loja que já existe.

Este spec cobre só a parte que dá alavancagem real em cima do que já
existe: **estrutura SKAG na criação de campanha + negative keywords
(lista universal + mineração de termos reais) + uma skill que orquestra
o fluxo completo**.

## Objetivo

1. `criar_campanha` passa a criar de fato uma estrutura SKAG (hoje cria
   um grupo com N keywords e 1 anúncio — viola o princípio de 1
   keyword = 1 grupo) e aplica os defaults de geo-targeting que o
   vídeo recomenda (presence, não presence-or-interest).
2. Nova tool `negative_keywords` pra aplicar uma lista universal
   (reaproveitável entre campanhas via shared set) e minerar termos de
   busca reais que estão gastando dinheiro à toa.
3. Nova skill `skag-ads` que orienta o Claude a montar o fluxo
   completo em conversa: keyword research real → filtro de intenção →
   URL de produto real → `criar_campanha` → `negative_keywords`.

## Fora de escopo (Fase 2 futura, não detalhado aqui)

- **Landing pages novas** (Next.js do zero, como no vídeo) — os 3 sites
  já existem; o "Final URL" do anúncio sempre aponta pra uma página
  real de produto/categoria via `catalogo_produtos`, nunca uma página
  criada especificamente pro anúncio.
- **Pipeline de ROAS real via CRM** (parâmetros de URL → campos ocultos
  → CRM → CSV → offline conversion import no Google Ads) — depende de
  um CRM que não existe no projeto hoje. GA4 já tem ecommerce tracking
  nativo (compra = conversão real, sem precisar desse pipeline manual)
  — ver `TOOLS/GA4`.
- **Dashboard de auditoria dedicado** — já existe `auditoria-ads` (hoje
  wrapper de `LEGADO/agente-ads`) cobrindo parte disso; reconciliar com
  a arquitetura nova é uma decisão separada, fora deste spec.
- **Geração de imagens/logo nos anúncios** — o vídeo já nota que isso é
  arriscado sem curadoria (imagem de baixa qualidade reduz CTR); fica
  pra quando alguém decidir cuidar da curadoria visual por site.

## Arquitetura

### 1. Extensão de `criar_campanha`

**Schema atual** (`tool.json`): um `nome_campanha`, uma lista
`palavras_chave` (N keywords no mesmo grupo), um único `titulos`/
`descricoes` (um anúncio só). `construtor.py` cria 1 orçamento, 1
campanha, 1 grupo, N keywords nesse grupo, 1 anúncio.

**Schema novo**: substitui `palavras_chave`/`titulos`/`descricoes`/
`url_final` de nível de campanha por `grupos_anuncio`:

```json
{
  "nome_campanha": "...",
  "orcamento_diario_brl": 100,
  "lance_inicial_brl": 2.5,
  "geo_target_type": "PRESENCE",
  "paises_excluidos": ["geoTargetConstants/..."],
  "grupos_anuncio": [
    {
      "keyword": {"texto": "whey protein isolado", "tipo_correspondencia": "PHRASE"},
      "url_final": "https://.../produto/whey-protein-isolado",
      "anuncios": [
        {"titulos": ["...", "...", "..."], "descricoes": ["...", "..."], "headline_pinada": "whey protein isolado"}
      ]
    }
  ]
}
```

Regras:
- `tipo_correspondencia` default vira `PHRASE` (era `BROAD`) — reflete
  a recomendação do vídeo (broad gasta dinheiro com semântica
  irrelevante; exact é bom demais pra restringir volume).
- **Um `grupos_anuncio[i]` = exatamente 1 keyword** (SKAG de verdade,
  não uma lista). Validação rejeita mais de uma keyword por grupo.
- Cada grupo pode ter N `anuncios` (split test) em vez de 1 fixo — mais
  de um anúncio no mesmo `AdGroupAdService.mutate` (loop, não uma
  chamada só).
- `headline_pinada`, se presente, vira o primeiro `AdTextAsset` do
  anúncio com `pinned_field = HEADLINE_1` (hoje nenhum headline é
  pinado).
- `geo_target_type`: novo campo obrigatório, enum `PRESENCE` |
  `PRESENCE_OR_INTEREST`, default `PRESENCE`. Hoje `_criar_targeting`
  não seta esse campo no `CampaignCriterion.location` — a API assume
  `PRESENCE_OR_INTEREST`, que é o oposto do que o vídeo recomenda (evita
  gente fora do país "interessada" na região aparecer no leilão).
- `paises_excluidos`: lista opcional de `geoTargetConstants` negativos
  (`CampaignCriterionOperation` com `negative = True`) — decisão de
  negócio por site (não travar hardcoded; cada site decide se quer
  excluir todo o resto do mundo ou não).

`validacao.py` ganha: `grupos_anuncio` não vazio; cada grupo tem
`keyword.texto`; cada grupo tem ≥1 anúncio; cada anúncio segue as
mesmas regras mínimas de hoje (≥3 títulos, ≥2 descrições).

`construtor.py`: `_criar_grupo_anuncio`/`_criar_keywords`/`_criar_anuncio`
passam a rodar em loop por item de `grupos_anuncio` (hoje rodam uma vez
só); nome do grupo passa a ser derivado da keyword (ex:
`"{nome_campanha} — {keyword.texto}"`) em vez do `"grupo 1"` fixo
atual.

### 2. Nova tool `TOOLS/ADWORDS/negative_keywords/`

`tool.json` com duas ações (`acao: "aplicar_universal" |
"minerar_termos_reais"`), consistente com o padrão de uma tool por
script + `input_schema` já usado no projeto.

**`universal.md`** (por site, em `TOOLS/ADWORDS/negative_keywords/
<site>/universal.md` — nunca compartilhado entre sites, cada e-commerce
tem público e concorrentes diferentes): lista de termos por categoria
(emprego/carreira, curso/DIY, concorrente, pesquisa gratuita/definição)
— ponto de partida inspirado no vídeo, mas cada site ajusta a própria
lista manualmente ao longo do tempo.

**`aplicar_universal(site)`**:
1. Lê `universal.md` do site.
2. Cria (ou reaproveita, se já existir) um `SharedSet` do tipo
   `NEGATIVE_KEYWORDS` pro cliente.
3. Adiciona os termos como `SharedCriterion` nesse shared set (só os
   que ainda não estão lá — idempotente).
4. Linka o shared set a todas as campanhas ativas do site via
   `CampaignSharedSetService` (se ainda não linkado).
`requer_confirmacao: true` (é escrita na conta).

**`minerar_termos_reais(site, dias=30)`**:
1. GAQL contra `search_term_view` dos últimos N dias, filtrando termos
   com custo > 0 e conversões = 0.
2. Retorna a lista bruta (termo, campanha, custo, cliques) — **só
   relatório**, não aplica nada. `requer_confirmacao: false` (leitura).
3. Aplicar as sugestões dessa mineração como negativa é uma chamada
   separada e explícita de `aplicar_universal`-like (adicionar ao
   shared set do site) — sempre com confirmação humana antes, igual o
   vídeo enfatiza ("you approve that report").

### 3. Nova skill `.claude/skills/skag-ads/SKILL.md`

Segue o padrão das skills de auditoria já existentes (frontmatter
`description` explicando quando usar, corpo em markdown orientando o
Claude, sem código novo — só orquestração das tools acima). Fluxo que a
skill descreve:

1. Rodar `GenerateKeywordIdeas` (Keyword Planner) pro serviço/produto e
   cidade/site em questão — usar dado real de volume, nunca inventar
   keyword de memória (mesma disciplina de `learn-api`/`learn-redis`).
2. Filtrar por intenção: descartar termos de emprego/carreira, curso/
   DIY, concorrente direto — mesma lógica do `universal.md` do site.
3. Pra cada keyword aprovada, achar a URL de produto/categoria real via
   `catalogo_produtos` (nunca propor criar página nova).
4. Montar a proposta `grupos_anuncio` (1 keyword por grupo, ≥2
   variações de anúncio pra permitir split test) e chamar
   `criar_campanha` — sempre pausada, confirmação humana explícita
   antes de criar de fato (mesmo guardrail de hoje).
5. Ao final, rodar `negative_keywords.aplicar_universal` pro site.
6. Não use esta skill pra otimizar campanha existente — isso é
   `minerar_termos_reais` isolado ou `auditoria-ads`, não criação nova.

## Testes

Mesmo padrão do projeto (`test_validacao.py`, `test_sitemap.py`):
- `test_validacao.py` (atualizado): novo schema `grupos_anuncio` —
  grupo sem keyword, grupo com >1 keyword (deve rejeitar), anúncio
  abaixo do mínimo de títulos/descrições, grupo sem nenhum anúncio.
- `test_negative_keywords.py` (novo): parsing de `universal.md` →
  lista de termos; lógica pura de filtro de `minerar_termos_reais`
  (custo > 0 e conversões = 0) com dados de exemplo — sem chamar a API
  de verdade.
- `construtor.py` e a chamada de mutate de `negative_keywords`
  continuam sem teste automatizado (mesmo padrão já usado nas outras
  tools — só a lógica pura é testada, a chamada de rede é validada
  manualmente).

## Verificação manual

(a) Chamar `criar_campanha` com 2 `grupos_anuncio` (2 keywords
diferentes) e conferir no Google Ads que viraram 2 ad groups
separados, cada um com 1 keyword e seus próprios anúncios, campanha
pausada, `geo_target_type` presence aplicado. (b) Rodar
`negative_keywords.aplicar_universal` num site de teste e conferir que
o shared set aparece linkado às campanhas do site. (c) Rodar
`minerar_termos_reais` numa conta com histórico e conferir que retorna
termos com custo > 0 sem inventar dado.
