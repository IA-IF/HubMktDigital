---
name: learn-redis
description: >
  Coleta a referência REAL e COMPLETA (bruta, sem curadoria) da lib Redis
  instalada neste projeto (redisvl + redis-py) via introspecção ao vivo do
  pacote instalado — não da memória de treinamento — e salva em
  REDIS/DOCS/raw/. Use quando o usuário pedir pra "aprender"/"pesquisar"
  o que o Redis/RedisVL consegue fazer, especialmente pra decidir como
  processar/indexar o material bruto já coletado em TOOLS/<GRUPO>/DOCS/
  (discover_tool, busca vetorial). Mesma disciplina do learn-api: não
  resumir, não escolher "os métodos mais relevantes" — dado bruto completo,
  a curadoria fica pra quando alguém for usar de verdade.
---

# Learn Redis — coleta bruta e completa, mesma disciplina do learn-api

**Uso restrito a desenvolvimento, só com Claude Code.** Ver
`.claude/skills/learn-api/SKILL.md` pro racional completo (raso vs. bruto)
— vale palavra por palavra aqui, só troca a fonte (API do Google →
biblioteca Python instalada).

## Por que introspectar a lib instalada, não ler doc da internet

A versão instalada é a que importa — `redisvl` muda rápido (é lib jovem,
0.x). Memória de treinamento pode descrever uma versão antiga com API
diferente. `pip show redisvl` primeiro pra saber a versão exata antes de
qualquer coisa, e documentar essa versão junto do dump.

Docs oficiais baixadas já existem em `REDIS/DOCS/` (`agent-concepts.md`,
`ai-agent-builder.md`, `memory-and-performance.md`) — não duplicar, só
complementar com o que só dá pra saber introspectando o pacote de verdade
(assinatura exata de método, parâmetros aceitos na versão instalada).

## Como coletar

```python
import json, inspect, pkgutil
import redisvl

def dump_modulo(modulo, vistos=None):
    vistos = vistos or set()
    resultado = {}
    for nome in dir(modulo):
        if nome.startswith('_'):
            continue
        obj = getattr(modulo, nome)
        if inspect.isclass(obj) or inspect.isfunction(obj):
            try:
                assinatura = str(inspect.signature(obj))
            except (ValueError, TypeError):
                assinatura = None
            resultado[nome] = {
                'tipo': 'classe' if inspect.isclass(obj) else 'funcao',
                'assinatura': assinatura,
                'docstring': inspect.getdoc(obj),
                'modulo_origem': getattr(obj, '__module__', None),
            }
            if inspect.isclass(obj):
                metodos = {}
                for mnome, mobj in inspect.getmembers(obj, predicate=inspect.isfunction):
                    if mnome.startswith('_') and mnome != '__init__':
                        continue
                    try:
                        massinatura = str(inspect.signature(mobj))
                    except (ValueError, TypeError):
                        massinatura = None
                    metodos[mnome] = {'assinatura': massinatura, 'docstring': inspect.getdoc(mobj)}
                resultado[nome]['metodos'] = metodos
    return resultado

# repetir por submodulo relevante: redisvl.index, redisvl.query,
# redisvl.schema, redisvl.extensions.message_history,
# redisvl.extensions.llmcache, redisvl.utils.vectorize (embeddings)
```

Documentar também o comando Redis nativo por trás (RediSearch/`FT.*`) via
`redis.commands.search` (`redis-py`), pelo mesmo motivo: `redisvl` é uma
camada sobre isso, útil saber os dois níveis.

## Materializar o resultado

`REDIS/DOCS/raw/redisvl_<submodulo>.json` — um arquivo por submódulo
introspectado, dump direto (classe → métodos → assinatura + docstring),
sem resumir. `REDIS/DOCS/raw/README.md` só com data, versão exata
(`pip show redisvl`/`pip show redis`), e lista de arquivos — mesmo formato
do `TOOLS/<GRUPO>/DOCS/README.md`.

## O que esta skill NÃO faz

- Não decide qual mecanismo do RedisVL usar pro `discover_tool` — só
  levanta o que existe de verdade na versão instalada, pra essa decisão
  ser tomada depois com informação completa.
- Não resume nem filtra "os métodos mais úteis".
- Não lê nada de `LEGADO/`.
