# POC — execução genérica ADWORDS (schema + mutate) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** POC pequeno e validável (não a migração inteira da spec
`docs/superpowers/specs/2026-07-27-execucao-generica-apis-design.md`):
construir só 2 primitivas genéricas pro ADWORDS —
`ads_consultar_schema` e `ads_mutate` — e validar com um teste REAL que
elas resolvem o caso concreto que expôs o problema (segmentação por
proximidade, o equivalente real a "por CEP"). `criar_campanha`
continua existindo, intocado, até essa validação passar.

**Architecture:** Duas tools novas em `TOOLS/ADWORDS/`, seguindo o
padrão já estabelecido no projeto (`tool.json` + script Python
standalone, dispatch via `agentes.py`/`executor_tools.py` existente —
nenhum dos dois precisa mudar). `ads_mutate` usa o mecanismo genérico
que a própria API do Google Ads já tem pra isso — `GoogleAdsService.
Mutate` com `MutateOperation` (um wrapper que aceita QUALQUER tipo de
operação através de um oneof) — em vez de precisar mapear cada tipo de
recurso pro seu Service/método específico (que tem pluralização
irregular, ex: `CampaignCriterion` → `mutate_campaign_criteria`, não
`mutate_campaign_criterions`).

**Tech Stack:** Python 3.11+, `google-ads` (já instalado, v31.1.0/API
v24), `pytest`.

## Global Constraints

- Não mexe em `TOOLS/ADWORDS/criar_campanha/` nem em `AGENTES/julio/`.
- Lógica pura (transformação de nomes, montagem de campos) tem teste
  automatizado (`pytest`). A chamada real à API (mutate de verdade) é
  validada por teste REAL manual (mesmo padrão já usado nesta sessão
  pro `criar_campanha` e pro `analise_ads`) — não por mock, já que o
  objetivo do POC é justamente provar que funciona contra a API de
  verdade.
- Guardrail inegociável preservado: `Campaign` criada via `ads_mutate`
  sempre nasce `PAUSED`, sem exceção, mesmo que não pedido.

---

## File Structure

- Create: `TOOLS/ADWORDS/ads_consultar_schema/tool.json`
- Create: `TOOLS/ADWORDS/ads_consultar_schema/consultar_schema.py`
- Create: `TOOLS/ADWORDS/ads_mutate/tool.json`
- Create: `TOOLS/ADWORDS/ads_mutate/mutate.py`
- Create: `TOOLS/ADWORDS/ads_mutate/test_mutate.py` (lógica pura)

---

### Task 1: `ads_consultar_schema` — schema real de qualquer recurso, ao vivo

**Files:**
- Create: `TOOLS/ADWORDS/ads_consultar_schema/consultar_schema.py`
- Create: `TOOLS/ADWORDS/ads_consultar_schema/tool.json`

**Interfaces:**
- Produces: `consultar_schema(tipo_recurso: str) -> dict` — devolve
  `{"name": <nome completo>, "fields": [{"name", "number", "type",
  "label", "message_type"?, "enum_type"?, "enum_values"?, "oneof"?}]}`
  pra qualquer classe de mensagem protobuf indexável no pacote
  `google.ads.googleads.v24` (mesma técnica de introspecção já usada
  em `TOOLS/ADWORDS/DOCS/raw/mutate_mensagens.json` nesta sessão, só
  que como tool ao vivo em vez de dump estático). `{"erro": "..."}` se
  o tipo não for encontrado.
- CLI: `python consultar_schema.py <site> <tipo_recurso>` — imprime
  JSON no stdout (mesmo padrão de todas as outras tools do projeto).

- [x] **Step 1: Write the failing test**

```python
# TOOLS/ADWORDS/ads_consultar_schema/test_consultar_schema.py
from consultar_schema import consultar_schema


def test_consultar_schema_devolve_campos_reais_de_campaign():
    resultado = consultar_schema("Campaign")
    nomes_campos = [f["name"] for f in resultado["fields"]]
    assert "campaign_budget" in nomes_campos
    assert "maximize_conversions" in nomes_campos
    assert resultado["name"].endswith("Campaign")


def test_consultar_schema_devolve_campos_de_proximity_info():
    resultado = consultar_schema("ProximityInfo")
    nomes_campos = [f["name"] for f in resultado["fields"]]
    assert "geo_point" in nomes_campos or "radius" in nomes_campos


def test_consultar_schema_erro_pra_tipo_desconhecido():
    resultado = consultar_schema("TipoQueNaoExiste123")
    assert "erro" in resultado
```

- [x] **Step 2: Run test to verify it fails**

Run: `cd TOOLS/ADWORDS/ads_consultar_schema && python -m pytest test_consultar_schema.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'consultar_schema'`

- [x] **Step 3: Write minimal implementation**

```python
# TOOLS/ADWORDS/ads_consultar_schema/consultar_schema.py
"""Consulta ao vivo o schema real (via introspecção protobuf) de
qualquer tipo de mensagem da API do Google Ads instalada -- generaliza
a coleta estatica feita em TOOLS/ADWORDS/DOCS/raw/mutate_mensagens.json
pra uma tool que o agente pode chamar sob demanda, pra QUALQUER tipo
de recurso, nao so os que alguem catalogou de antemao.
"""
import importlib
import json
import pkgutil
import sys

import google.ads.googleads.v24 as v24_pkg

LABEL_NOMES = {1: "OPTIONAL", 2: "REQUIRED", 3: "REPEATED"}
TIPO_NOMES = {
    1: "DOUBLE", 2: "FLOAT", 3: "INT64", 4: "UINT64", 5: "INT32",
    6: "FIXED64", 7: "FIXED32", 8: "BOOL", 9: "STRING", 10: "GROUP",
    11: "MESSAGE", 12: "BYTES", 13: "UINT32", 14: "ENUM", 15: "SFIXED32",
    16: "SFIXED64", 17: "SINT32", 18: "SINT64",
}

_INDICE_CLASSES: dict[str, type] = {}


def _indexar_classes() -> None:
    if _INDICE_CLASSES:
        return
    for _, nome_modulo, _ in pkgutil.walk_packages(v24_pkg.__path__, prefix="google.ads.googleads.v24."):
        if ".types" not in nome_modulo:
            continue
        try:
            mod = importlib.import_module(nome_modulo)
        except Exception:
            continue
        for atributo in dir(mod):
            if atributo.startswith("_"):
                continue
            obj = getattr(mod, atributo)
            if atributo in _INDICE_CLASSES:
                continue
            if hasattr(obj, "pb") and callable(getattr(obj, "pb", None)):
                try:
                    if hasattr(obj.pb(), "DESCRIPTOR"):
                        _INDICE_CLASSES[atributo] = obj
                except Exception:
                    continue


def consultar_schema(tipo_recurso: str) -> dict:
    _indexar_classes()
    classe = _INDICE_CLASSES.get(tipo_recurso)
    if classe is None:
        return {"erro": f"tipo de recurso desconhecido: {tipo_recurso}"}
    descriptor = classe.pb().DESCRIPTOR
    campos = []
    for f in descriptor.fields:
        campo = {
            "name": f.name, "number": f.number,
            "type": TIPO_NOMES.get(f.type, f.type),
            "label": LABEL_NOMES.get(f.label, f.label),
        }
        if f.type == 11 and f.message_type is not None:
            campo["message_type"] = f.message_type.name
        if f.type == 14 and f.enum_type is not None:
            campo["enum_type"] = f.enum_type.name
            campo["enum_values"] = [v.name for v in f.enum_type.values]
        if f.containing_oneof is not None:
            campo["oneof"] = f.containing_oneof.name
        campos.append(campo)
    return {"name": descriptor.full_name, "fields": campos}


if __name__ == "__main__":
    tipo_recurso_arg = sys.argv[2] if len(sys.argv) > 2 else sys.argv[1]
    print(json.dumps(consultar_schema(tipo_recurso_arg), ensure_ascii=False, indent=2))
```

- [x] **Step 4: Run test to verify it passes**

Run: `cd TOOLS/ADWORDS/ads_consultar_schema && python -m pytest test_consultar_schema.py -v`
Expected: PASS (3 tests)

- [x] **Step 5: Write `tool.json`**

```json
{
  "name": "ads_consultar_schema",
  "plataforma": "ADWORDS",
  "description": "Consulta os campos reais de QUALQUER tipo de recurso/mensagem da API do Google Ads (ex: Campaign, CampaignCriterion, ProximityInfo, UserList). Chame ANTES de usar ads_mutate pra saber exatamente quais campos existem e seus tipos -- nunca adivinhe um campo sem consultar primeiro.",
  "script": "TOOLS/ADWORDS/ads_consultar_schema/consultar_schema.py",
  "modo_entrada": "argv",
  "input_schema": {
    "type": "object",
    "properties": {
      "tipo_recurso": {"type": "string", "description": "Nome exato do tipo, ex: 'Campaign', 'CampaignCriterion', 'ProximityInfo', 'UserList'."}
    },
    "required": ["tipo_recurso"]
  }
}
```

- [x] **Step 6: Commit**

```bash
git add TOOLS/ADWORDS/ads_consultar_schema/
git commit -m "feat: ads_consultar_schema - schema real de qualquer recurso Ads, ao vivo (POC execucao generica)"
```

---

### Task 2: `ads_mutate` — criar/atualizar/remover qualquer recurso, genérico

**Files:**
- Create: `TOOLS/ADWORDS/ads_mutate/mutate.py`
- Create: `TOOLS/ADWORDS/ads_mutate/tool.json`
- Create: `TOOLS/ADWORDS/ads_mutate/test_mutate.py`

**Interfaces:**
- Consumes: nada do Task 1 diretamente (mas o AGENTE usa os dois juntos
  na prática: consulta schema, depois monta o mutate).
- Produces:
  - `nome_campo_operacao(recurso: str) -> str` — pura, transforma
    `"Campaign"` → `"campaign_operation"`, `"CampaignCriterion"` →
    `"campaign_criterion_operation"` (PascalCase → snake_case + sufixo
    `_operation` — o nome do campo oneof em `MutateOperation` que
    corresponde a esse tipo de recurso).
  - `aplicar_campos(mensagem, campos: dict) -> None` — pura (modifica
    `mensagem` in-place), aplica um dict de campos recursivamente
    (dict aninhado → sub-mensagem; valor escalar → `setattr` direto).
  - `montar_mutate_operation(recurso: str, operacao: str, campos: dict) -> MutateOperation`
    — monta a operação completa: cria `{recurso}Operation`, aplica
    `campos` no sub-campo certo (`.create`/`.update`/`.remove`
    conforme `operacao`), força `status="PAUSED"` se
    `recurso == "Campaign" and operacao == "create"` (guardrail
    inegociável, sobrepõe qualquer valor em `campos`), e embrulha no
    `MutateOperation` certo usando `nome_campo_operacao`.
  - `executar_mutate(site: str, recurso: str, operacao: str, campos: dict) -> dict`
    — usa `GoogleAdsClient` de verdade + `GoogleAdsService.mutate`
    (o endpoint genérico que aceita qualquer `MutateOperation`), site
    igual ao padrão já usado em `criar_campanha.py` (`.env` raiz +
    `SITES/<site>/.env`). Devolve `{"ok": True, "resource_name": ...}`
    ou `{"ok": False, "erros": [...]}` em caso de erro da API (mesmo
    formato que `criar_campanha` já usa, pro `agentes.py`/
    `executor_tools.py` reconhecerem sem mudar nada).

- [x] **Step 1: Write the failing tests (só lógica pura, sem API real)**

```python
# TOOLS/ADWORDS/ads_mutate/test_mutate.py
from mutate import aplicar_campos, montar_mutate_operation, nome_campo_operacao


def test_nome_campo_operacao_simples():
    assert nome_campo_operacao("Campaign") == "campaign_operation"


def test_nome_campo_operacao_composto():
    assert nome_campo_operacao("CampaignCriterion") == "campaign_criterion_operation"
    assert nome_campo_operacao("AdGroupAd") == "ad_group_ad_operation"
    assert nome_campo_operacao("UserList") == "user_list_operation"


def test_montar_mutate_operation_campaign_forca_paused_mesmo_se_pedido_enabled():
    campos = {"name": "Teste", "advertising_channel_type": "SEARCH", "status": "ENABLED"}
    mutate_op = montar_mutate_operation("Campaign", "create", campos)
    assert mutate_op.campaign_operation.create.status.name == "PAUSED"
    assert mutate_op.campaign_operation.create.name == "Teste"


def test_montar_mutate_operation_campaign_forca_paused_quando_omitido():
    campos = {"name": "Teste"}
    mutate_op = montar_mutate_operation("Campaign", "create", campos)
    assert mutate_op.campaign_operation.create.status.name == "PAUSED"


def test_montar_mutate_operation_outro_recurso_nao_forca_status():
    campos = {"keyword": {"text": "patinho cubo", "match_type": "BROAD"}}
    mutate_op = montar_mutate_operation("AdGroupCriterion", "create", campos)
    criacao = mutate_op.ad_group_criterion_operation.create
    assert criacao.keyword.text == "patinho cubo"
    # guardrail de status=PAUSED e so pra Campaign -- outro recurso nao tem status forcado
    assert criacao.status.name == "UNSPECIFIED"


def test_aplicar_campos_dict_aninhado_vira_submensagem():
    from google.ads.googleads.v24.resources.types.ad_group_criterion import AdGroupCriterion
    criterio = AdGroupCriterion()
    aplicar_campos(criterio, {"keyword": {"text": "patinho cubo", "match_type": "BROAD"}})
    assert criterio.keyword.text == "patinho cubo"
    assert criterio.keyword.match_type.name == "BROAD"
```

- [x] **Step 2: Run tests to verify they fail**

Run: `cd TOOLS/ADWORDS/ads_mutate && python -m pytest test_mutate.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'mutate'`

- [x] **Step 3: Write minimal implementation**

```python
# TOOLS/ADWORDS/ads_mutate/mutate.py
"""Cria/atualiza/remove QUALQUER recurso do Google Ads atraves do
mecanismo generico que a propria API ja oferece pra isso --
GoogleAdsService.Mutate com MutateOperation (um wrapper que aceita
qualquer tipo de operacao via oneof). Substitui a abordagem de uma
tool por capacidade (TOOLS/ADWORDS/criar_campanha) por um unico
executor que o agente usa pra QUALQUER recurso, informado por
ads_consultar_schema.

Guardrail inegociavel preservado (igual criar_campanha): Campaign
criada aqui sempre nasce PAUSED, mesmo que campos peca outra coisa --
ativar e sempre decisao manual fora desta tool.
"""
import importlib
import json
import pkgutil
import re
import sys
from pathlib import Path

import google.ads.googleads.v24 as v24_pkg
from dotenv import dotenv_values
from google.ads.googleads.client import GoogleAdsClient

REPO_ROOT = Path(__file__).resolve().parents[3]

# Indice de classes de mensagem protobuf indexavel por nome -- mesma
# tecnica de TOOLS/ADWORDS/ads_consultar_schema/consultar_schema.py,
# duplicada aqui (nao importada de la) de proposito: cada tool e um
# processo independente, ver AGENTES/julio/agentes.py docstring.
_INDICE_CLASSES: dict[str, type] = {}


def _indexar_classes() -> None:
    if _INDICE_CLASSES:
        return
    for _, nome_modulo, _ in pkgutil.walk_packages(v24_pkg.__path__, prefix="google.ads.googleads.v24."):
        if ".types" not in nome_modulo:
            continue
        try:
            mod = importlib.import_module(nome_modulo)
        except Exception:
            continue
        for atributo in dir(mod):
            if atributo.startswith("_") or atributo in _INDICE_CLASSES:
                continue
            obj = getattr(mod, atributo)
            if hasattr(obj, "pb") and callable(getattr(obj, "pb", None)):
                try:
                    if hasattr(obj.pb(), "DESCRIPTOR"):
                        _INDICE_CLASSES[atributo] = obj
                except Exception:
                    continue


def nome_campo_operacao(recurso: str) -> str:
    """'CampaignCriterion' -> 'campaign_criterion_operation'."""
    snake = re.sub(r"(?<!^)(?=[A-Z])", "_", recurso).lower()
    return f"{snake}_operation"


def aplicar_campos(mensagem, campos: dict) -> None:
    for chave, valor in campos.items():
        if isinstance(valor, dict):
            aplicar_campos(getattr(mensagem, chave), valor)
        else:
            setattr(mensagem, chave, valor)


def montar_mutate_operation(recurso: str, operacao: str, campos: dict):
    _indexar_classes()
    from google.ads.googleads.v24.services.types.google_ads_service import MutateOperation

    nome_operation = f"{recurso}Operation"
    classe_operation = _INDICE_CLASSES.get(nome_operation)
    if classe_operation is None:
        raise ValueError(f"tipo de operacao desconhecido: {nome_operation}")

    op = classe_operation()
    campos_finais = dict(campos)
    if recurso == "Campaign" and operacao == "create":
        campos_finais["status"] = "PAUSED"

    if operacao == "create":
        aplicar_campos(op.create, campos_finais)
    elif operacao == "update":
        aplicar_campos(op.update, campos_finais)
    elif operacao == "remove":
        op.remove = campos_finais["resource_name"]
    else:
        raise ValueError(f"operacao desconhecida: {operacao}")

    mutate_op = MutateOperation()
    setattr(mutate_op, nome_campo_operacao(recurso), op)
    return mutate_op


def executar_mutate(site: str, recurso: str, operacao: str, campos: dict) -> dict:
    comum = dotenv_values(REPO_ROOT / ".env")
    do_site = dotenv_values(REPO_ROOT / "SITES" / site / ".env")
    if "GOOGLE_ADS_CUSTOMER_ID" not in do_site or not do_site["GOOGLE_ADS_CUSTOMER_ID"]:
        return {"ok": False, "erros": [f"site '{site}' sem GOOGLE_ADS_CUSTOMER_ID configurado"]}

    cfg = {
        "developer_token": comum["GOOGLE_ADS_DEVELOPER_TOKEN"],
        "client_id": comum["GOOGLE_ADS_CLIENT_ID"],
        "client_secret": comum["GOOGLE_ADS_CLIENT_SECRET"],
        "refresh_token": comum["GOOGLE_ADS_REFRESH_TOKEN"],
        "use_proto_plus": True,
    }
    if comum.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID"):
        cfg["login_customer_id"] = comum["GOOGLE_ADS_LOGIN_CUSTOMER_ID"]
    client = GoogleAdsClient.load_from_dict(cfg)
    cid = do_site["GOOGLE_ADS_CUSTOMER_ID"].replace("-", "")

    try:
        mutate_op = montar_mutate_operation(recurso, operacao, campos)
    except ValueError as exc:
        return {"ok": False, "erros": [str(exc)]}

    service = client.get_service("GoogleAdsService")
    try:
        resposta = service.mutate(customer_id=cid, mutate_operations=[mutate_op])
    except Exception as exc:  # noqa: BLE001 -- GoogleAdsException tem forma variavel
        return {"ok": False, "erros": [str(exc)]}

    resultado = resposta.mutate_operation_responses[0]
    campo_resposta = resultado._pb.WhichOneof("response")
    resource_name = getattr(getattr(resultado, campo_resposta), "resource_name", None)
    return {"ok": True, "resource_name": resource_name}


if __name__ == "__main__":
    site_arg = sys.argv[1] if len(sys.argv) > 1 else "3gfoods"
    entrada = json.load(sys.stdin)
    print(json.dumps(
        executar_mutate(site_arg, entrada["recurso"], entrada["operacao"], entrada["campos"]),
        ensure_ascii=False, indent=2,
    ))
```

- [x] **Step 4: Run tests to verify they pass**

Run: `cd TOOLS/ADWORDS/ads_mutate && python -m pytest test_mutate.py -v`
Expected: PASS (6 tests) — nenhum precisa de credencial real, só monta a mensagem protobuf em memória.

- [x] **Step 5: Write `tool.json`**

```json
{
  "name": "ads_mutate",
  "plataforma": "ADWORDS",
  "description": "Cria, atualiza ou remove QUALQUER recurso do Google Ads (Campaign, CampaignBudget, CampaignCriterion, AdGroup, AdGroupCriterion, AdGroupAd, UserList, etc.) -- generico, nao limitado a um tipo especifico. Use ads_consultar_schema ANTES pra saber os campos exatos do recurso que voce precisa. Campanhas (recurso=Campaign, operacao=create) sempre nascem PAUSADAS automaticamente, mesmo que nao pedido -- ativar e sempre acao manual fora desta tool.",
  "script": "TOOLS/ADWORDS/ads_mutate/mutate.py",
  "modo_entrada": "stdin",
  "requer_confirmacao": true,
  "input_schema": {
    "type": "object",
    "properties": {
      "recurso": {"type": "string", "description": "Tipo do recurso, ex: 'Campaign', 'CampaignCriterion', 'UserList'. Consulte ads_consultar_schema se tiver duvida."},
      "operacao": {"type": "string", "description": "'create', 'update' ou 'remove'."},
      "campos": {"type": "object", "description": "Campos do recurso, conforme o schema real (consulte ads_consultar_schema). Pode aninhar objetos pra sub-mensagens (ex: {\"location\": {\"geo_target_constant\": \"...\"}})."}
    },
    "required": ["recurso", "operacao", "campos"]
  }
}
```

- [x] **Step 6: Commit**

```bash
git add TOOLS/ADWORDS/ads_mutate/
git commit -m "feat: ads_mutate - criar/atualizar/remover qualquer recurso Ads, generico (POC execucao generica)"
```

---

### Task 3: Validação REAL — proximidade (equivalente a "CEP") sem código específico

**Files:** nenhum arquivo novo — só um teste manual/smoke, documentado
no resultado (adicionar ao `ARQUITETURA/entendimento.md` depois).

- [x] **Step 1:** Rodar, via `ARQUITETURA/nucleo/agente.processar_turno`
  (cliente Anthropic real, `executor_tools.criar_executor_tool`
  apontando só pras 2 tools novas + `ads_gaql` NÃO incluída neste POC),
  um pedido tipo: *"crie uma campanha de search pausada pro produto X
  da 3G Foods, segmentada num raio de 5km ao redor do endereço da
  loja"*.
- [x] **Step 2:** Confirmar no histórico que o agente:
  (a) chamou `ads_consultar_schema("ProximityInfo")` e/ou
  `ads_consultar_schema("CampaignCriterion")` sem ter sido instruído
  a fazer isso especificamente:
  (b) construiu um `ads_mutate(recurso="CampaignCriterion", ...)` com
  `proximity` preenchido corretamente (radius + geo_point ou address),
  sem nenhum código escrito por mim pra "targeting por proximidade"
  especificamente.
- [x] **Step 3:** Se falhar: documentar o motivo exato (não é uma
  falha genérica — é dado real pra saber se o POC precisa de ajuste
  na `description` das tools, no `aplicar_campos`, ou se a abordagem
  em si tem um problema mais fundo).

---

## Depois deste POC

Se a validação do Task 3 passar: decidir com o usuário se
`criar_campanha` é retirado (movido pra referência) e se o padrão
generaliza pra GA4/GTM/Search Console (ver spec completa). Se falhar:
ajustar só o que a evidência apontar — não expandir escopo antes de
fechar o POC.
