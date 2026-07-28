# Núcleo v2 — seleção de site por conversa + memória de perfil de cliente — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fechar os 2 gaps confirmados na auditoria do núcleo v2 (ver
`ARQUITETURA/entendimento.md`): (1) `main.py` hoje fixa o site pro
processo inteiro, violando a regra dura do `CLAUDE.md` ("site sempre
explícito na conversa"); (2) zero memória de perfil de cliente
(`roas_alvo` etc.), então o agente não tem de onde aprender dado real
do cliente entre conversas.

**Architecture:** Os dois seguem o MESMO padrão já usado pro resumo
(Plano 3): chave no Redis, lida no início de cada mensagem, escrita
por uma tool. **Site** é por CHAT (cada conversa tem seu próprio site
selecionado) — como nenhuma tool subprocess recebe `chat_id` (só
`site`), `selecionar_site` é tratado no `main.py` (a camada de
assembly, não o núcleo genérico `agente.py`): intercepta essa tool
específica pra gravar no Redis direto, e reconstrói `tools`/
`executar_tool` a cada mensagem com base no site atual daquele chat —
sem adicionar special-casing em `agente.py`, que continua 100%
genérico. **Perfil de cliente** é por SITE (não por chat) — `site` já
é passado a toda tool via argv, então `atualizar_perfil_cliente` é uma
tool subprocess NORMAL (mesmo padrão de `registrar_pedido_futuro`),
sem precisar de tratamento especial em lugar nenhum.

**Tech Stack:** Python 3.11+, `pytest`, Redis real (hash
`cliente:<site>:perfil`, mesmo esquema já usado em
`AGENTES/julio/perfil_cliente.py`, pra compatibilidade se algum dia
precisar ler o mesmo dado de lá).

## Global Constraints

- Não mexe em `AGENTES/julio/**`.
- `agente.py` não ganha NENHUM caso especial novo — toda a lógica de
  site fica em `main.py`.
- Teste real (não só mock) validando que o agente pergunta o site
  quando não selecionado, e usa o certo depois de selecionado.

---

## File Structure

- Modify: `ARQUITETURA/nucleo/memoria.py` (`carregar_site`/
  `salvar_site`, `carregar_perfil_cliente`/`montar_system_com_perfil`)
- Modify: `ARQUITETURA/nucleo/tests/test_memoria.py`
- Create: `TOOLS/GERAL/atualizar_perfil_cliente/atualizar.py` + `tool.json`
- Modify: `ARQUITETURA/nucleo/main.py`

---

### Task 1: `memoria.py` — site e perfil de cliente (mesma forma do resumo)

**Files:**
- Modify: `ARQUITETURA/nucleo/memoria.py`
- Modify: `ARQUITETURA/nucleo/tests/test_memoria.py`

**Interfaces:**
- Produces:
  - `carregar_site(cliente_redis, chat_id, prefixo="site:") -> str | None`
  - `salvar_site(cliente_redis, chat_id, site, prefixo="site:") -> None`
  - `carregar_perfil_cliente(cliente_redis, site) -> dict` — usa
    `hgetall` na chave `cliente:{site}:perfil` (mesmo esquema do
    `AGENTES/julio/perfil_cliente.py`).
  - `montar_system_com_perfil(system_base: str, site: str | None, perfil: dict, campos_esperados: list[str]) -> str` —
    se `site` for `None`, devolve `system_base` intacto (nenhum site
    selecionado ainda, nada de perfil pra mostrar). Senão, anexa uma
    seção "=== Perfil do cliente (site) ===" com os campos já
    preenchidos e uma linha "Campos ainda faltando: ...".

- [ ] **Step 1: Write the failing tests**

```python
# adicionar em ARQUITETURA/nucleo/tests/test_memoria.py
from ARQUITETURA.nucleo.memoria import (
    carregar_perfil_cliente,
    carregar_site,
    montar_system_com_perfil,
    salvar_site,
)


def test_carregar_site_none_quando_nunca_selecionado():
    cliente = ClienteRedisFake()
    assert carregar_site(cliente, "chat1") is None


def test_salvar_e_carregar_site():
    cliente = ClienteRedisFake()
    salvar_site(cliente, "chat1", "3gfoods")
    assert carregar_site(cliente, "chat1") == "3gfoods"


def test_carregar_perfil_cliente_vazio_quando_nunca_salvo():
    class ClienteRedisFakeHash(ClienteRedisFake):
        def hgetall(self, chave):
            return {}
    cliente = ClienteRedisFakeHash()
    assert carregar_perfil_cliente(cliente, "3gfoods") == {}


def test_montar_system_sem_site_nao_mostra_perfil():
    resultado = montar_system_com_perfil("Base.", None, {}, ["roas_alvo"])
    assert resultado == "Base."


def test_montar_system_com_site_mostra_perfil_e_campos_faltando():
    perfil = {"roas_alvo": "400%"}
    resultado = montar_system_com_perfil("Base.", "3gfoods", perfil, ["roas_alvo", "publico_alvo"])
    assert "Base." in resultado
    assert "roas_alvo: 400%" in resultado
    assert "publico_alvo" in resultado  # campo faltando mencionado
```

Nota: `ClienteRedisFake` (já existe em `test_memoria.py`) só implementa
`get`/`set` — o teste de `carregar_perfil_cliente` precisa de
`hgetall`, daí a subclasse local `ClienteRedisFakeHash` só nesse teste.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest ARQUITETURA/nucleo/tests/test_memoria.py -v`
Expected: FAIL (`ImportError`)

- [ ] **Step 3: Write minimal implementation**

```python
# adicionar em ARQUITETURA/nucleo/memoria.py
def carregar_site(cliente_redis, chat_id: str, prefixo: str = "site:") -> str | None:
    return cliente_redis.get(f"{prefixo}{chat_id}")


def salvar_site(cliente_redis, chat_id: str, site: str, prefixo: str = "site:") -> None:
    cliente_redis.set(f"{prefixo}{chat_id}", site)


def carregar_perfil_cliente(cliente_redis, site: str) -> dict:
    return cliente_redis.hgetall(f"cliente:{site}:perfil")


def montar_system_com_perfil(
    system_base: str, site: str | None, perfil: dict, campos_esperados: list[str],
) -> str:
    if site is None:
        return system_base
    linhas_perfil = [f"- {campo}: {perfil[campo]}" for campo in campos_esperados if campo in perfil]
    bloco_perfil = "\n".join(linhas_perfil) if linhas_perfil else "(perfil ainda vazio)"
    faltando = [c for c in campos_esperados if c not in perfil]
    texto_faltando = ", ".join(faltando) if faltando else "nenhum"
    return (
        f"{system_base}\n\n=== Perfil do cliente ({site}) ===\n{bloco_perfil}\n"
        f"Campos ainda faltando: {texto_faltando}. Só pergunte um campo faltando "
        "quando uma tarefa real precisar dele -- nunca faça entrevista completa "
        "de uma vez. Quando o humano responder, chame `atualizar_perfil_cliente`."
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest ARQUITETURA/ -v`
Expected: PASS (todos + os 5 novos)

- [ ] **Step 5: Commit**

```bash
git add ARQUITETURA/nucleo/memoria.py ARQUITETURA/nucleo/tests/test_memoria.py
git commit -m "feat: site por conversa e perfil de cliente no memoria.py (nucleo v2)"
```

---

### Task 2: `atualizar_perfil_cliente` — tool subprocess normal (sem caso especial)

**Files:**
- Create: `TOOLS/GERAL/atualizar_perfil_cliente/atualizar.py`
- Create: `TOOLS/GERAL/atualizar_perfil_cliente/tool.json`

**Interfaces:**
- Produces: `atualizar(site: str, campo: str, valor: str) -> dict` —
  valida `campo` contra a MESMA lista de `AGENTES/julio/
  perfil_cliente.py` (`CAMPOS`), grava via `hset` em
  `cliente:{site}:perfil`. `{"ok": False, "erros": [...]}` se campo
  desconhecido (`FalhaPermanente`-shaped, sem precisar da exceção —
  já é o formato que `executor_tools.criar_executor_tool` reconhece).

- [ ] **Step 1:** Escrever `atualizar.py` (dispatch `stdin`, mesmo
  padrão de `registrar_pedido_futuro/registrar.py`):

```python
# TOOLS/GERAL/atualizar_perfil_cliente/atualizar.py
"""Atualiza um campo do perfil de cliente (por site) no Redis --
mesmo esquema de AGENTES/julio/perfil_cliente.py (hash
cliente:<site>:perfil), pra compatibilidade se algum dia precisar ler
o mesmo dado de lá.
"""
import json
import sys
from pathlib import Path

from dotenv import dotenv_values

REPO_ROOT = Path(__file__).resolve().parents[3]

CAMPOS = [
    "quem_e_cliente", "o_que_vende", "pra_quem_vende",
    "publico_alvo", "orcamento_diario_tipico", "roas_alvo", "produtos_em_foco",
]


def atualizar(site: str, campo: str, valor: str) -> dict:
    if campo not in CAMPOS:
        return {"ok": False, "erros": [f"campo de perfil desconhecido: {campo!r} (validos: {CAMPOS})"]}

    env = dotenv_values(REPO_ROOT / "REDIS" / ".env")
    if not env.get("REDIS_URL"):
        return {"ok": False, "erros": ["REDIS_URL nao configurado em REDIS/.env"]}

    import redis
    cliente = redis.Redis.from_url(env["REDIS_URL"], decode_responses=True)
    cliente.hset(f"cliente:{site}:perfil", campo, valor)
    return {"ok": True}


if __name__ == "__main__":
    site_arg = sys.argv[1] if len(sys.argv) > 1 else "3gfoods"
    entrada = json.load(sys.stdin)
    print(json.dumps(atualizar(site_arg, entrada["campo"], entrada["valor"]), ensure_ascii=False, indent=2))
```

- [ ] **Step 2:** Escrever `tool.json`:

```json
{
  "name": "atualizar_perfil_cliente",
  "plataforma": "geral",
  "description": "Chame quando o humano disser algo que preenche um campo do perfil do cliente do site atual (quem e o cliente, o que vende, pra quem vende, publico-alvo, orcamento diario, ROAS-alvo, produtos em foco). So chame com o que ele disse explicitamente, nunca invente um valor.",
  "script": "TOOLS/GERAL/atualizar_perfil_cliente/atualizar.py",
  "modo_entrada": "stdin",
  "input_schema": {
    "type": "object",
    "properties": {
      "campo": {"type": "string", "description": "quem_e_cliente, o_que_vende, pra_quem_vende, publico_alvo, orcamento_diario_tipico, roas_alvo ou produtos_em_foco."},
      "valor": {"type": "string"}
    },
    "required": ["campo", "valor"]
  }
}
```

- [ ] **Step 3:** Testar de verdade contra Redis real:

```bash
cd TOOLS/GERAL/atualizar_perfil_cliente
echo '{"campo": "roas_alvo", "valor": "400%"}' | python atualizar.py 3gfoods
```
Expected: `{"ok": true}`, e confirmar via `HGETALL cliente:3gfoods:perfil` no Redis real.

- [ ] **Step 4: Commit**

```bash
git add TOOLS/GERAL/atualizar_perfil_cliente/
git commit -m "feat: atualizar_perfil_cliente - tool normal, sem caso especial (nucleo v2)"
```

---

### Task 3: `main.py` — site por chat (reconstroi tools/executor por mensagem) + perfil no prompt

**Files:**
- Modify: `ARQUITETURA/nucleo/main.py`

**Interfaces:**
- Produces: `processar_mensagem` agora: carrega o site do CHAT atual
  (`carregar_site`); se `None`, monta `tools`/`executar_tool` só com
  `selecionar_site` (definido em código, não em `TOOLS/`, já que só
  existe pra mutar estado de conversa) + o resto do catálogo BASE
  (`registrar_pedido_futuro`); se site selecionado, monta o catálogo
  completo pra aquele site (via `criar_executor_tool` com o site
  certo) + injeta o perfil no `system`. `executar_tool` intercepta
  `selecionar_site` especificamente (única exceção, documentada) pra
  gravar via `salvar_site` -- todo o resto delega pro executor
  genérico normal.

- [ ] **Step 1:** Ler `main.py` atual e reescrever `processar_mensagem`/
  `rodar`/`montar_dependencias` pra: (a) não fixar `site`/`tools`/
  `executar_tool` uma vez só no início do processo; (b) recarregar por
  mensagem, com base no site daquele chat especificamente.

- [ ] **Step 2:** Rodar teste REAL (não mock): mensagem nova sem site
  selecionado → agente pergunta qual site (não assume); depois de
  `selecionar_site` chamado, próxima mensagem já usa o catálogo/site
  certo, e o perfil (se algum campo já setado) aparece no `system`.

- [ ] **Step 3: Commit**

```bash
git add ARQUITETURA/nucleo/main.py
git commit -m "feat: site por conversa + perfil no prompt, sem caso especial em agente.py (nucleo v2)"
```

---

## Depois deste plano

Os 2 gaps da auditoria completa estão fechados. Próximo trabalho em
aberto: decompor `criar_campanha`-equivalente em tools componíveis
onde fizer sentido (já resolvido pra ADWORDS via `ads_mutate`), e a
otimização/limpeza contínua de GA4/GTM/Search Console conforme forem
usadas de verdade.
