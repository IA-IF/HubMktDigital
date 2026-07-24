---
name: learn-api
description: >
  Coleta a referência REAL e COMPLETA (bruta, sem curadoria) de uma API do
  Google (GA4, GTM, Ads, Search Console) via introspecção ao vivo — não da
  memória de treinamento — e salva em TOOLS/<GRUPO>/DOCS/. Use quando o
  usuário pedir pra "aprender"/"pesquisar" uma API, "coletar referência",
  ou preparar material bruto pra indexar depois no Redis. Não use memória
  de treinamento pra listar campos/métodos de API — sempre introspecte ao
  vivo. Não resuma nem filtre "os mais relevantes" — a curadoria é etapa
  separada (feita depois, com Redis/embeddings), não desta skill.
---

# Learn API — coleta bruta e completa, não resumo curado

**Uso restrito a desenvolvimento, só com Claude Code.** Não tem lugar em
produção — é preparo de material pra uma etapa futura de digestão via
Redis (embeddings/busca vetorial, ver `TOOLS/GOOGLE_API/` e `inteligencia.md`
Etapa 2, `discover_tool`). Essa digestão **não é feita por esta skill nem
por mim decidindo à mão o que é "destaque"** — é feita depois, por outro
processo, sobre o dado bruto que esta skill deixa pronto.

## Erro já cometido nesta sessão (não repetir)

Na primeira passada, o `TOOLS/ADWORDS/DOCS/learn.md` saiu como um resumo
com contagens por categoria e uns "destaques" escolhidos por mim (5-6
serviços de 112, alguns campos de exemplo). Achado raso pelo usuário —
com razão: se um erro de código acontecer, ou o humano pedir algo fora
desses "destaques", o arquivo não ajuda em nada, porque **eu decidi por
antecipação o que seria relevante**, sem saber ainda o que vai ser
perguntado. Isso é o oposto do objetivo. A referência tem que ser completa
o bastante pra responder qualquer pergunta futura, não só as que eu
imaginei agora.

## O que "completo" significa na prática

Pra cada campo/método/recurso da API, capturar **todos os atributos que a
própria API expõe sobre ele** — não só nome + 1 linha de descrição:

- GA4 (`getMetadata`): `apiName`, `uiName`, `description`, `category`, e
  pra métricas também `type`/`expression` quando existir — **de TODAS as
  376 dimensões e 140 métricas**, não uma amostra por categoria.
- GTM/Search Console (discovery `_rootDesc`): pra cada método, **o objeto
  inteiro** (`description` completa, não só a 1ª linha; `parameters` com
  cada campo aceito; `request`/`response` schema) — não só
  `nome | HTTP | resumo`.
- Ads (`GoogleAdsFieldService`): **os 3.050 campos inteiros**, um por
  linha, com `name`, `category`, `data_type`, `selectable`, `filterable`,
  `sortable`, `selectable_with` (com quais outros campos pode combinar) —
  não só a contagem por categoria e 2 exemplos de recurso.

## Formato de saída: JSON bruto, não markdown curado

Markdown com tabela força a escolher o que cabe na linha — isso já é
curadoria. Formato correto:

`TOOLS/<GRUPO>/DOCS/raw/<recurso>.json` — dump direto da resposta da API
(ou do discovery document), sem reescrever nem resumir campos. Um arquivo
por API/recurso quando fizer sentido separar (ex: GA4 pode ter
`raw/admin_methods.json`, `raw/data_methods.json`, `raw/metadata.json`
com as 516 dimensões+métricas completas).

Um `TOOLS/<GRUPO>/DOCS/README.md` curto (não `learn.md`) só com:
1. Quando/como esse dump foi gerado (data, credenciais usadas, comando)
2. Onde cada arquivo `raw/*.json` está e o que ele cobre
3. **Nada de "destaques" ou "isso é interessante porque"** — isso é
   julgamento de relevância pra uma pergunta específica, que ainda não
   existe. Fica pra quando o Redis indexar e alguém perguntar algo de
   verdade.

## Como coletar (adaptar por plataforma)

Credenciais **só da raiz do projeto novo** (`.env` + `SITES/<site>/.env`)
— nunca de `LEGADO/`, mesma regra do `protocolo-teste-tools`.

```python
import json
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

creds = Credentials(token=None, scopes=[...], client_id=..., client_secret=..., refresh_token=..., token_uri="https://oauth2.googleapis.com/token")
service = build("<nome_api>", "<versao>", credentials=creds, cache_discovery=False)

# GTM/Search Console/GA4 Admin/GA4 Data: discovery document inteiro, sem filtrar nada
Path("raw/discovery.json").write_text(json.dumps(service._rootDesc, ensure_ascii=False, indent=2))

# GA4 Data: metadata completo da propriedade (376+140 campos inteiros)
meta = service.properties().getMetadata(name=f"{property_path}/metadata").execute()
Path("raw/metadata.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2))
```

Ads (sem discovery document, ver `TOOLS/GOOGLE_API/auth.json`):
```python
gaf = client.get_service("GoogleAdsFieldService")
resp = gaf.search_google_ads_fields(query="SELECT name, category, data_type, selectable, filterable, sortable, selectable_with")
campos = [{"name": r.name, "category": r.category.name, "data_type": r.data_type.name,
           "selectable": r.selectable, "filterable": r.filterable, "sortable": r.sortable,
           "selectable_with": list(r.selectable_with)} for r in resp]
Path("raw/google_ads_fields.json").write_text(json.dumps(campos, ensure_ascii=False, indent=2))

# lista de servicos instalados na lib, sem filtrar quais "parecem uteis"
import pkgutil, google.ads.googleads.v24.services.services as svc, os
nomes = sorted(d for d in os.listdir(svc.__path__[0]) if d.endswith("_service") and not d.startswith("__"))
Path("raw/services.json").write_text(json.dumps(nomes, ensure_ascii=False, indent=2))
```

APIs/versões conhecidas: GA4 Admin `analyticsadmin` v1beta, GA4 Data
`analyticsdata` v1beta, GTM `tagmanager` v2, Search Console `searchconsole`
v1.

## O que esta skill NÃO faz

- Não resume, não filtra "os mais relevantes", não decide o que é
  destaque — dado bruto e completo, sempre.
- Não decide sozinha quais campos/métodos viram ferramenta nova em
  `TOOLS/` — isso é outra etapa, depois da digestão via Redis.
- Não roda nem lê nada de `LEGADO/` — mesmo se um catálogo parecido já
  existir lá, refaz do zero na arquitetura nova.
