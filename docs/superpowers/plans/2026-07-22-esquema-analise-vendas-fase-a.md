# Esquema de Análise de Vendas — Fase A (GA4) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir a Fase A do esquema de análise de vendas (spec:
`docs/superpowers/specs/2026-07-22-esquema-analise-vendas-design.md`) —
funil de conversão, split de sessão por canal com taxa de conversão, e
taxas de ecommerce (add-to-cart, checkout completion, AOV) — usando só
dados reais do GA4 via `runReport`, sem depender de Ads/GTM/Search
Console (essas entram nas Fases B/C/D, fora deste plano).

**Architecture:** Cada cálculo (funil, split de canal, taxas de
ecommerce) é uma função pura testável (recebe dado já buscado, devolve
número calculado) separada da função de integração que busca o dado real
via `googleapiclient` (`analyticsdata` v1beta `runReport`). Um módulo
orquestrador (`analise_vendas.py`) busca os 3 conjuntos de dado reais e
aplica os 3 cálculos, imprimindo um JSON só.

**Tech Stack:** Python, `googleapiclient.discovery.build("analyticsdata",
"v1beta", ...)`, `google.oauth2.credentials.Credentials`, `pytest` pros
testes das funções puras.

## Global Constraints

- Credenciais **só** de `.env` (raiz do projeto) + `SITES/<site>/.env` —
  nunca de `LEGADO/` (ver `.claude/skills/protocolo-teste-tools/SKILL.md`
  e `.claude/skills/learn-api/SKILL.md`).
- Nenhum código deste plano lê nem importa nada de `LEGADO/`.
- Todas as 5 etapas do funil, os campos de canal e os campos de ecommerce
  usados devem ser exatamente os documentados em
  `TOOLS/GA4/DOCS/raw/metadata_3gfoods.json` (não inventar nome de campo
  — conferir contra esse arquivo se tiver dúvida de um `apiName`).
- Etapas do funil, na ordem: `session_start`, `view_item`, `add_to_cart`,
  `begin_checkout`, `purchase` (definição oficial do relatório "Jornada
  de compra" do GA4, documentada na spec).
- Este plano cobre só a Fase A (GA4 sozinho). Não implementar nada de
  Ads/GTM/Search Console aqui.

---

### Task 1: Cálculo do funil de conversão (função pura)

**Files:**
- Create: `TOOLS/GA4/analise_vendas/funil.py`
- Test: `TOOLS/GA4/analise_vendas/test_funil.py`

**Interfaces:**
- Produces: `ETAPAS_FUNIL: list[str]` (as 5 etapas, na ordem), e
  `calcular_funil(contagens: dict[str, int]) -> list[dict]` — cada dict
  tem `etapa` (str), `contagem` (int), `taxa_retencao` (float | None),
  `taxa_abandono` (float | None). Etapa 0 sempre tem
  `taxa_retencao=1.0`/`taxa_abandono=0.0`. Etapa i>0:
  `taxa_retencao = contagens[etapa_i] / contagens[etapa_{i-1}]` (arredondado
  a 4 casas), `taxa_abandono = 1 - taxa_retencao`. Se
  `contagens[etapa_{i-1}] == 0`, ambos ficam `None` (não dividir por
  zero).

- [ ] **Step 1: Escrever o teste que falha**

```python
# TOOLS/GA4/analise_vendas/test_funil.py
from funil import ETAPAS_FUNIL, calcular_funil


def test_etapas_funil_na_ordem_certa():
    assert ETAPAS_FUNIL == [
        "session_start", "view_item", "add_to_cart", "begin_checkout", "purchase",
    ]


def test_calcular_funil_com_queda_normal():
    contagens = {
        "session_start": 1000,
        "view_item": 400,
        "add_to_cart": 100,
        "begin_checkout": 50,
        "purchase": 20,
    }
    resultado = calcular_funil(contagens)

    assert len(resultado) == 5
    assert resultado[0] == {
        "etapa": "session_start", "contagem": 1000,
        "taxa_retencao": 1.0, "taxa_abandono": 0.0,
    }
    assert resultado[1]["etapa"] == "view_item"
    assert resultado[1]["contagem"] == 400
    assert resultado[1]["taxa_retencao"] == 0.4
    assert resultado[1]["taxa_abandono"] == 0.6
    assert resultado[4]["etapa"] == "purchase"
    assert resultado[4]["taxa_retencao"] == 0.4


def test_calcular_funil_com_etapa_zerada_nao_divide_por_zero():
    contagens = {
        "session_start": 1000,
        "view_item": 0,
        "add_to_cart": 0,
        "begin_checkout": 0,
        "purchase": 0,
    }
    resultado = calcular_funil(contagens)

    assert resultado[1]["taxa_retencao"] is None
    assert resultado[1]["taxa_abandono"] is None


def test_calcular_funil_aceita_contagem_faltando_como_zero():
    contagens = {"session_start": 500}
    resultado = calcular_funil(contagens)

    assert resultado[1]["contagem"] == 0
    assert resultado[1]["taxa_retencao"] == 0.0
```

- [ ] **Step 2: Rodar o teste e confirmar que falha**

Run: `cd TOOLS/GA4/analise_vendas && python -m pytest test_funil.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'funil'`

- [ ] **Step 3: Implementar `funil.py`**

```python
# TOOLS/GA4/analise_vendas/funil.py
"""Calculo puro do funil de conversao (Fase A do esquema de analise de
vendas, ver docs/superpowers/specs/2026-07-22-esquema-analise-vendas-design.md).

Etapas na mesma ordem oficial do relatorio "Jornada de compra" do GA4
(funil fechado): session_start -> view_item -> add_to_cart ->
begin_checkout -> purchase.
"""

ETAPAS_FUNIL = ["session_start", "view_item", "add_to_cart", "begin_checkout", "purchase"]


def calcular_funil(contagens: dict[str, int]) -> list[dict]:
    resultado = []
    anterior = None
    for etapa in ETAPAS_FUNIL:
        contagem = contagens.get(etapa, 0)
        if anterior is None:
            taxa_retencao, taxa_abandono = 1.0, 0.0
        elif anterior == 0:
            taxa_retencao, taxa_abandono = None, None
        else:
            taxa_retencao = round(contagem / anterior, 4)
            taxa_abandono = round(1 - taxa_retencao, 4)
        resultado.append({
            "etapa": etapa,
            "contagem": contagem,
            "taxa_retencao": taxa_retencao,
            "taxa_abandono": taxa_abandono,
        })
        anterior = contagem
    return resultado
```

- [ ] **Step 4: Rodar o teste e confirmar que passa**

Run: `cd TOOLS/GA4/analise_vendas && python -m pytest test_funil.py -v`
Expected: `4 passed`

- [ ] **Step 5: Commit**

```bash
git add TOOLS/GA4/analise_vendas/funil.py TOOLS/GA4/analise_vendas/test_funil.py
git commit -m "Fase A (esquema de analise de vendas): calculo puro do funil de conversao"
```

---

### Task 2: Split de sessão por canal com taxa de conversão (função pura)

**Files:**
- Create: `TOOLS/GA4/analise_vendas/canais.py`
- Test: `TOOLS/GA4/analise_vendas/test_canais.py`

**Interfaces:**
- Consumes: nada de tasks anteriores (independente).
- Produces: `calcular_split_canal(linhas: list[dict]) -> list[dict]` —
  cada linha de entrada é `{"canal": str, "sessoes": int, "compras": int}`;
  a saída acrescenta `"taxa_conversao": float | None`
  (`compras / sessoes`, arredondado a 4 casas, `None` se `sessoes == 0`),
  e vem **ordenada por `sessoes` decrescente**.

- [ ] **Step 1: Escrever o teste que falha**

```python
# TOOLS/GA4/analise_vendas/test_canais.py
from canais import calcular_split_canal


def test_calcular_split_canal_ordena_por_sessoes_e_calcula_taxa():
    linhas = [
        {"canal": "Organic Search", "sessoes": 200, "compras": 7},
        {"canal": "Paid Search", "sessoes": 500, "compras": 4},
        {"canal": "Direct", "sessoes": 100, "compras": 1},
    ]
    resultado = calcular_split_canal(linhas)

    assert [r["canal"] for r in resultado] == ["Paid Search", "Organic Search", "Direct"]
    assert resultado[0]["taxa_conversao"] == 0.008
    assert resultado[1]["taxa_conversao"] == 0.035
    assert resultado[2]["taxa_conversao"] == 0.01


def test_calcular_split_canal_com_zero_sessoes_nao_divide_por_zero():
    linhas = [{"canal": "Referral", "sessoes": 0, "compras": 0}]
    resultado = calcular_split_canal(linhas)

    assert resultado[0]["taxa_conversao"] is None
```

- [ ] **Step 2: Rodar o teste e confirmar que falha**

Run: `cd TOOLS/GA4/analise_vendas && python -m pytest test_canais.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'canais'`

- [ ] **Step 3: Implementar `canais.py`**

```python
# TOOLS/GA4/analise_vendas/canais.py
"""Split de sessao por canal + taxa de conversao por canal (Fase A do
esquema de analise de vendas). Dado bruto vem de runReport dimensionado
por sessionDefaultChannelGroup (ver TOOLS/GA4/DOCS/raw/metadata_3gfoods.json).
"""


def calcular_split_canal(linhas: list[dict]) -> list[dict]:
    resultado = []
    for linha in linhas:
        sessoes = linha["sessoes"]
        compras = linha["compras"]
        taxa = round(compras / sessoes, 4) if sessoes else None
        resultado.append({**linha, "taxa_conversao": taxa})
    return sorted(resultado, key=lambda r: r["sessoes"], reverse=True)
```

- [ ] **Step 4: Rodar o teste e confirmar que passa**

Run: `cd TOOLS/GA4/analise_vendas && python -m pytest test_canais.py -v`
Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
git add TOOLS/GA4/analise_vendas/canais.py TOOLS/GA4/analise_vendas/test_canais.py
git commit -m "Fase A (esquema de analise de vendas): split de canal com taxa de conversao"
```

---

### Task 3: Taxas de ecommerce — add-to-cart, checkout completion, AOV (função pura)

**Files:**
- Create: `TOOLS/GA4/analise_vendas/ecommerce_taxas.py`
- Test: `TOOLS/GA4/analise_vendas/test_ecommerce_taxas.py`

**Interfaces:**
- Consumes: nada de tasks anteriores (independente).
- Produces: `calcular_taxas_ecommerce(dados: dict) -> dict`. `dados` tem
  as chaves `items_viewed`, `add_to_carts`, `checkouts`,
  `ecommerce_purchases`, `purchase_revenue`, `transactions` (todas
  `int`/`float`). Retorna
  `{"add_to_cart_rate": float | None, "checkout_completion_rate": float | None, "aov": float | None}`:
  - `add_to_cart_rate = add_to_carts / items_viewed` (arredondado a 4
    casas; `None` se `items_viewed == 0`)
  - `checkout_completion_rate = ecommerce_purchases / checkouts`
    (arredondado a 4 casas; `None` se `checkouts == 0`)
  - `aov = purchase_revenue / transactions` (arredondado a 2 casas;
    `None` se `transactions == 0`)

- [ ] **Step 1: Escrever o teste que falha**

```python
# TOOLS/GA4/analise_vendas/test_ecommerce_taxas.py
from ecommerce_taxas import calcular_taxas_ecommerce


def test_calcular_taxas_ecommerce_com_dado_normal():
    dados = {
        "items_viewed": 500,
        "add_to_carts": 80,
        "checkouts": 50,
        "ecommerce_purchases": 35,
        "purchase_revenue": 5250.0,
        "transactions": 35,
    }
    resultado = calcular_taxas_ecommerce(dados)

    assert resultado["add_to_cart_rate"] == 0.16
    assert resultado["checkout_completion_rate"] == 0.7
    assert resultado["aov"] == 150.0


def test_calcular_taxas_ecommerce_com_denominadores_zerados():
    dados = {
        "items_viewed": 0, "add_to_carts": 0, "checkouts": 0,
        "ecommerce_purchases": 0, "purchase_revenue": 0.0, "transactions": 0,
    }
    resultado = calcular_taxas_ecommerce(dados)

    assert resultado == {
        "add_to_cart_rate": None, "checkout_completion_rate": None, "aov": None,
    }
```

- [ ] **Step 2: Rodar o teste e confirmar que falha**

Run: `cd TOOLS/GA4/analise_vendas && python -m pytest test_ecommerce_taxas.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'ecommerce_taxas'`

- [ ] **Step 3: Implementar `ecommerce_taxas.py`**

```python
# TOOLS/GA4/analise_vendas/ecommerce_taxas.py
"""Taxas de ecommerce (Fase A do esquema de analise de vendas): add-to-cart
rate, checkout completion rate, AOV. Formulas e benchmarks documentados em
docs/superpowers/specs/2026-07-22-esquema-analise-vendas-design.md
(add-to-cart >=12% e checkout completion >=70% sao os benchmarks de
mercado citados na spec, nao um valor fixo do codigo).
"""


def calcular_taxas_ecommerce(dados: dict) -> dict:
    items_viewed = dados["items_viewed"]
    checkouts = dados["checkouts"]
    transactions = dados["transactions"]

    add_to_cart_rate = round(dados["add_to_carts"] / items_viewed, 4) if items_viewed else None
    checkout_completion_rate = (
        round(dados["ecommerce_purchases"] / checkouts, 4) if checkouts else None
    )
    aov = round(dados["purchase_revenue"] / transactions, 2) if transactions else None

    return {
        "add_to_cart_rate": add_to_cart_rate,
        "checkout_completion_rate": checkout_completion_rate,
        "aov": aov,
    }
```

- [ ] **Step 4: Rodar o teste e confirmar que passa**

Run: `cd TOOLS/GA4/analise_vendas && python -m pytest test_ecommerce_taxas.py -v`
Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
git add TOOLS/GA4/analise_vendas/ecommerce_taxas.py TOOLS/GA4/analise_vendas/test_ecommerce_taxas.py
git commit -m "Fase A (esquema de analise de vendas): taxas de ecommerce (add-to-cart/checkout/AOV)"
```

---

### Task 4: Integração real com GA4 + orquestrador + verificação ao vivo

**Files:**
- Create: `TOOLS/GA4/analise_vendas/coleta.py`
- Create: `TOOLS/GA4/analise_vendas/analise_vendas.py`
- Create: `TOOLS/GA4/analise_vendas/tool.json`

**Interfaces:**
- Consumes: `funil.ETAPAS_FUNIL`, `funil.calcular_funil` (Task 1);
  `canais.calcular_split_canal` (Task 2);
  `ecommerce_taxas.calcular_taxas_ecommerce` (Task 3).
- Produces: `coleta.buscar_contagens_funil(service, property_path, dias) -> dict[str,int]`,
  `coleta.buscar_linhas_canal(service, property_path, dias) -> list[dict]`,
  `coleta.buscar_dados_ecommerce(service, property_path, dias) -> dict`,
  `analise_vendas.rodar_analise(site: str, dias: int = 7) -> dict` (função
  usada por qualquer chamador futuro, ex: uma ferramenta do agente
  conversacional).

Este é o único task que fala com a API de verdade — sem teste automatizado
(seguindo o `protocolo-teste-tools`: a parte determinística já foi testada
nas Tasks 1-3, aqui só se verifica ao vivo, rodando contra a conta real).

- [ ] **Step 1: Implementar `coleta.py`** (busca o dado bruto real via `runReport`)

```python
# TOOLS/GA4/analise_vendas/coleta.py
"""Busca o dado bruto real do GA4 pra alimentar funil.py/canais.py/
ecommerce_taxas.py. Unica peca deste modulo que fala com a API de
verdade -- ver Task 4 do plano, sem teste automatizado (a logica de
calculo ja foi testada nas pecas puras).
"""
from funil import ETAPAS_FUNIL


def buscar_contagens_funil(service, property_path: str, dias: int) -> dict[str, int]:
    corpo = {
        "dateRanges": [{"startDate": f"{dias}daysAgo", "endDate": "today"}],
        "dimensions": [{"name": "eventName"}],
        "metrics": [{"name": "eventCount"}],
        "dimensionFilter": {
            "filter": {
                "fieldName": "eventName",
                "inListFilter": {"values": ETAPAS_FUNIL},
            }
        },
    }
    resp = service.properties().runReport(property=property_path, body=corpo).execute()
    contagens = {}
    for row in resp.get("rows", []):
        nome_evento = row["dimensionValues"][0]["value"]
        contagem = int(row["metricValues"][0]["value"])
        contagens[nome_evento] = contagem
    return contagens


def buscar_linhas_canal(service, property_path: str, dias: int) -> list[dict]:
    corpo = {
        "dateRanges": [{"startDate": f"{dias}daysAgo", "endDate": "today"}],
        "dimensions": [{"name": "sessionDefaultChannelGroup"}],
        "metrics": [{"name": "sessions"}, {"name": "ecommercePurchases"}],
    }
    resp = service.properties().runReport(property=property_path, body=corpo).execute()
    linhas = []
    for row in resp.get("rows", []):
        linhas.append({
            "canal": row["dimensionValues"][0]["value"],
            "sessoes": int(row["metricValues"][0]["value"]),
            "compras": int(float(row["metricValues"][1]["value"])),
        })
    return linhas


def buscar_dados_ecommerce(service, property_path: str, dias: int) -> dict:
    metricas = ["itemsViewed", "addToCarts", "checkouts", "ecommercePurchases",
                "purchaseRevenue", "transactions"]
    corpo = {
        "dateRanges": [{"startDate": f"{dias}daysAgo", "endDate": "today"}],
        "metrics": [{"name": m} for m in metricas],
    }
    resp = service.properties().runReport(property=property_path, body=corpo).execute()
    if not resp.get("rows"):
        return {"items_viewed": 0, "add_to_carts": 0, "checkouts": 0,
                "ecommerce_purchases": 0, "purchase_revenue": 0.0, "transactions": 0}
    valores = resp["rows"][0]["metricValues"]
    return {
        "items_viewed": int(valores[0]["value"]),
        "add_to_carts": int(valores[1]["value"]),
        "checkouts": int(valores[2]["value"]),
        "ecommerce_purchases": int(float(valores[3]["value"])),
        "purchase_revenue": float(valores[4]["value"]),
        "transactions": int(float(valores[5]["value"])),
    }
```

- [ ] **Step 2: Implementar `analise_vendas.py`** (orquestrador + credenciais + CLI)

```python
# TOOLS/GA4/analise_vendas/analise_vendas.py
"""Fase A do esquema de analise de vendas (GA4 sozinho) -- ver
docs/superpowers/specs/2026-07-22-esquema-analise-vendas-design.md.

Uso:
    python analise_vendas.py [site] [dias]
    python analise_vendas.py 3gfoods 7

Credenciais so da raiz do projeto (.env + SITES/<site>/.env), nunca de
LEGADO/ -- mesma regra de TOOLS/GA4/DOCS/README.md.
"""
import json
import sys
from pathlib import Path

from dotenv import dotenv_values
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from canais import calcular_split_canal
from coleta import buscar_contagens_funil, buscar_dados_ecommerce, buscar_linhas_canal
from ecommerce_taxas import calcular_taxas_ecommerce
from funil import calcular_funil

REPO_ROOT = Path(__file__).resolve().parents[3]  # TOOLS/GA4/analise_vendas -> raiz do projeto
SCOPES = ["https://www.googleapis.com/auth/analytics.readonly"]


def _service_e_property(site: str):
    comum = dotenv_values(REPO_ROOT / ".env")
    do_site = dotenv_values(REPO_ROOT / "SITES" / site / ".env")
    creds = Credentials(
        token=None, scopes=SCOPES,
        client_id=comum["GA4_CLIENT_ID"], client_secret=comum["GA4_CLIENT_SECRET"],
        refresh_token=comum["GA4_REFRESH_TOKEN"], token_uri="https://oauth2.googleapis.com/token",
    )
    service = build("analyticsdata", "v1beta", credentials=creds, cache_discovery=False)
    property_path = f"properties/{do_site['GA4_PROPERTY_ID']}"
    return service, property_path


def rodar_analise(site: str, dias: int = 7) -> dict:
    service, property_path = _service_e_property(site)

    contagens_funil = buscar_contagens_funil(service, property_path, dias)
    linhas_canal = buscar_linhas_canal(service, property_path, dias)
    dados_ecommerce = buscar_dados_ecommerce(service, property_path, dias)

    return {
        "site": site,
        "periodo_dias": dias,
        "funil": calcular_funil(contagens_funil),
        "canais": calcular_split_canal(linhas_canal),
        "taxas_ecommerce": calcular_taxas_ecommerce(dados_ecommerce),
    }


if __name__ == "__main__":
    site_arg = sys.argv[1] if len(sys.argv) > 1 else "3gfoods"
    dias_arg = int(sys.argv[2]) if len(sys.argv) > 2 else 7
    print(json.dumps(rodar_analise(site_arg, dias_arg), ensure_ascii=False, indent=2))
```

- [ ] **Step 3: Rodar contra a conta real da 3G Foods e ler a saída de verdade**

Run: `cd TOOLS/GA4/analise_vendas && python analise_vendas.py 3gfoods 7`
Expected: um JSON com `funil` (5 etapas, `session_start` sendo a maior
contagem, decrescendo), `canais` (lista ordenada por sessões, com
`taxa_conversao` por canal), `taxas_ecommerce` (`add_to_cart_rate`,
`checkout_completion_rate`, `aov` todos números, não `null`, já que a 3G
Foods tem venda real nos últimos 7 dias).

Inspecionar a saída de verdade (não assumir que "rodou sem erro" =
"dado faz sentido") — conferir que `funil[0]["contagem"]` (session_start)
é maior ou igual a `funil[-1]["contagem"]` (purchase), e que a soma de
`sessoes` de todos os canais é uma ordem de grandeza razoável comparada ao
`session_start` do funil (não precisam bater exato — funil conta evento,
canal conta sessão — mas uma diferença de 100x indicaria erro).

- [ ] **Step 4: Criar o `tool.json`**

```json
{
  "name": "analise_vendas",
  "plataforma": "GA4",
  "description": "Fase A do esquema de analise de vendas: funil de conversao (session_start->purchase, com taxa de abandono por etapa), split de sessao por canal (pago/organico/direto) com taxa de conversao de cada canal, e taxas de ecommerce (add-to-cart rate, checkout completion rate, AOV). So leitura, dado real via runReport.",
  "input_schema": {
    "type": "object",
    "properties": {
      "dias": {
        "type": "integer",
        "description": "Quantos dias pra tras a partir de hoje. Opcional, default 7."
      }
    },
    "required": []
  }
}
```

- [ ] **Step 5: Commit**

```bash
git add TOOLS/GA4/analise_vendas/coleta.py TOOLS/GA4/analise_vendas/analise_vendas.py TOOLS/GA4/analise_vendas/tool.json
git commit -m "Fase A (esquema de analise de vendas): integracao real GA4 + orquestrador + tool.json"
```

---

## Self-Review

**Cobertura da spec (Fase A):** funil com abandono por etapa (Task 1),
split de canal com taxa de conversão (Task 2), add-to-cart rate/checkout
completion rate/AOV (Task 3), tudo com dado real via `runReport` (Task
4) — as 3 métricas da Fase A da spec estão cobertas. Fases B/C/D ficam
fora deste plano, como já delimitado no Global Constraints.

**Placeholders:** nenhum `TBD`/`TODO` — todas as funções têm corpo
completo e testes com valores concretos.

**Consistência de tipos:** `calcular_funil` (Task 1) devolve `list[dict]`
com chaves `etapa`/`contagem`/`taxa_retencao`/`taxa_abandono` — usado
assim em `analise_vendas.rodar_analise` (Task 4). `calcular_split_canal`
(Task 2) espera `list[dict]` com `canal`/`sessoes`/`compras` — é
exatamente o que `buscar_linhas_canal` (Task 4) produz. `calcular_taxas_ecommerce`
(Task 3) espera as 6 chaves que `buscar_dados_ecommerce` (Task 4)
produz — nomes conferidos um a um.
