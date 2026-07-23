"""Etapa 2 do inteligencia.md: indexa o catalogo real de ferramentas
(TOOLS/**/tool.json) no Redis pra busca vetorial (discover_tool).

Embedding local via HFTextVectorizer (sentence-transformers,
all-MiniLM-L6-v2) -- zero custo de API, roda na maquina, nao gasta token
Anthropic nem OpenAI so pra indexar.

Credenciais do Redis vem de REDIS/.env (REDIS_URL) -- e onde
agent.py/llm_router ja leem, nao e LEGADO, e a infra Redis compartilhada.

Uso:
    python discover_tool_indexar.py
"""
import json
from pathlib import Path

from dotenv import dotenv_values
from redisvl.index import SearchIndex
from redisvl.schema import IndexSchema
from redisvl.utils.vectorize import HFTextVectorizer

REPO_ROOT = Path(__file__).resolve().parents[2]
NOME_INDICE = "tools_catalog"

SCHEMA = {
    "index": {"name": NOME_INDICE, "prefix": "tool"},
    "fields": [
        {"name": "name", "type": "tag"},
        {"name": "plataforma", "type": "tag"},
        {"name": "description", "type": "text"},
        {"name": "tool_json_path", "type": "text"},
        {
            "name": "embedding",
            "type": "vector",
            "attrs": {"dims": 384, "distance_metric": "cosine", "algorithm": "flat", "datatype": "float32"},
        },
    ],
}


def _redis_url() -> str:
    valores = dotenv_values(REPO_ROOT / "REDIS" / ".env")
    return valores["REDIS_URL"]


def descobrir_tool_jsons() -> list[Path]:
    """Todo tool.json em TOOLS/, exceto dentro de DOCS/ (que e material
    bruto de referencia, nao ferramenta invocavel)."""
    return [
        p for p in (REPO_ROOT / "TOOLS").rglob("tool.json")
        if "DOCS" not in p.parts
    ]


def indexar() -> int:
    vectorizer = HFTextVectorizer(model="sentence-transformers/all-MiniLM-L6-v2")
    index = SearchIndex.from_dict(SCHEMA, redis_url=_redis_url())
    index.create(overwrite=True, drop=True)

    caminhos = descobrir_tool_jsons()
    registros = []
    for caminho in caminhos:
        dado = json.loads(caminho.read_text(encoding="utf-8"))
        texto = f"{dado['name']}: {dado['description']}"
        registros.append({
            "name": dado["name"],
            "plataforma": dado.get("plataforma", "GERAL"),
            "description": dado["description"],
            "tool_json_path": str(caminho.relative_to(REPO_ROOT)),
            "embedding": vectorizer.embed(texto, as_buffer=True),
        })

    index.load(registros)
    return len(registros)


if __name__ == "__main__":
    n = indexar()
    print(f"Indexadas {n} ferramentas no Redis (indice '{NOME_INDICE}')")
