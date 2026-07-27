"""Etapa 2 do inteligencia.md: busca vetorial no catalogo de tools (TOOLS/**/
tool.json) pra trazer so as K mais relevantes pra cada mensagem, em vez de
mandar o catalogo inteiro (dezenas/centenas de ferramentas) em toda chamada
ao Claude. Mesmo padrao do ToolSearch usado pelo Claude Code.

Uso:
    python discover_tool.py --reindex   # reconstroi o indice a partir dos
                                         # tool.json reais em TOOLS/
    python discover_tool.py "analiza o trafego"   # so pra debug manual
"""
import json
import sys
from pathlib import Path

import redis
from redisvl.index import SearchIndex
from redisvl.query import VectorQuery
from redisvl.schema import IndexSchema
from redisvl.utils.vectorize.text.huggingface import HFTextVectorizer

HUB_ROOT = Path(__file__).resolve().parents[2]
TOOLS_ROOT = HUB_ROOT / "TOOLS"

sys.path.insert(0, str(HUB_ROOT / "REDIS" / "llm_router"))
import config as llm_config  # noqa: E402

NOME_INDICE = "catalogo_tools"
LIMIAR_DISTANCIA = 0.7  # cosine distance; acima disso, o candidato nao entra

_SCHEMA = IndexSchema.from_dict({
    "index": {"name": NOME_INDICE, "prefix": "tool", "storage_type": "json"},
    "fields": [
        {"name": "name", "type": "tag"},
        {"name": "plataforma", "type": "tag"},
        {"name": "description", "type": "text"},
        # tool_json guarda o tool.json INTEIRO (script, modo_entrada,
        # requer_confirmacao, input_schema, o que mais aparecer no futuro)
        # -- assim um campo novo no tool.json nunca exige mexer neste
        # schema de novo, so reindexar.
        {"name": "tool_json", "type": "text"},
        {
            "name": "embedding",
            "type": "vector",
            "attrs": {"algorithm": "flat", "dims": 768, "distance_metric": "cosine", "datatype": "float32"},
        },
    ],
})


def _redis_client() -> redis.Redis:
    return redis.Redis.from_url(llm_config.redis_url(), decode_responses=True)


def catalogar_tools() -> list[dict]:
    """Le todo TOOLS/**/tool.json real e devolve a lista de tools cruas."""
    tools = []
    for caminho in sorted(TOOLS_ROOT.glob("**/tool.json")):
        tool = json.loads(caminho.read_text(encoding="utf-8"))
        tool["_caminho"] = str(caminho.relative_to(HUB_ROOT))
        tools.append(tool)
    return tools


def reindexar() -> int:
    """Reconstroi o indice do zero a partir do catalogo real. Retorna quantas
    tools foram indexadas."""
    client = _redis_client()
    vectorizer = HFTextVectorizer()
    index = SearchIndex(_SCHEMA, redis_client=client)
    index.create(overwrite=True, drop=True)

    tools = catalogar_tools()
    registros = []
    for tool in tools:
        tool_limpo = {k: v for k, v in tool.items() if not k.startswith("_")}
        texto_embedding = f"{tool['name']}: {tool['description']}"
        registros.append({
            "name": tool["name"],
            "plataforma": tool.get("plataforma", ""),
            "description": tool["description"],
            "tool_json": json.dumps(tool_limpo, ensure_ascii=False),
            "embedding": vectorizer.embed(texto_embedding),
        })
    if registros:
        index.load(registros, id_field="name")
    return len(registros)


def descobrir(mensagem: str, top_k: int = 5) -> list[dict]:
    """Busca vetorial: devolve ate top_k tools (tool.json completo de cada
    uma: name/plataforma/description/script/modo_entrada/input_schema/...)
    cuja descricao e mais proxima semanticamente da mensagem. Mensagem sem
    nenhum candidato relevante (ex: "oi") devolve lista vazia — nao forcamos
    top_k fixo abaixo do limiar de relevancia.

    top_k=5 (nao 3): teste real de 2026-07-27 achou "quero ver o trafego
    da adoro" cortando `analise_vendas` (GA4) fora por ser o 4o colocado
    (distancia 0.58, bem dentro do LIMIAR_DISTANCIA=0.7) -- top_k=3 era
    pequeno demais pro catalogo atual (7 tools), cortava candidato
    relevante antes do limiar de distancia entrar em acao.
    """
    client = _redis_client()
    vectorizer = HFTextVectorizer()
    index = SearchIndex(_SCHEMA, redis_client=client)

    vetor = vectorizer.embed(mensagem)
    query = VectorQuery(
        vector=vetor,
        vector_field_name="embedding",
        return_fields=["name", "tool_json"],
        num_results=top_k,
    )
    resultados = index.query(query)

    tools = []
    for r in resultados:
        if float(r["vector_distance"]) > LIMIAR_DISTANCIA:
            continue
        tools.append(json.loads(r["tool_json"]))
    return tools


if __name__ == "__main__":
    if "--reindex" in sys.argv:
        total = reindexar()
        print(f"{total} tools indexadas a partir de TOOLS/**/tool.json")
    else:
        mensagem_teste = sys.argv[1] if len(sys.argv) > 1 else "oi"
        print(json.dumps(descobrir(mensagem_teste), ensure_ascii=False, indent=2))
