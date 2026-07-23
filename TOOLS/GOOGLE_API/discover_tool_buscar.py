"""Etapa 2 do inteligencia.md: busca vetorial no catalogo indexado por
discover_tool_indexar.py -- devolve as top-K ferramentas mais relevantes
pra uma mensagem do usuario (ou lista vazia, se nada bater).

Uso:
    python discover_tool_buscar.py "quanto vendi essa semana" [top_k] [limiar]
"""
import json
import sys
from pathlib import Path

from dotenv import dotenv_values
from redisvl.index import SearchIndex
from redisvl.query import VectorQuery
from redisvl.utils.vectorize import HFTextVectorizer

from discover_tool_indexar import NOME_INDICE, SCHEMA

REPO_ROOT = Path(__file__).resolve().parents[2]


def _redis_url() -> str:
    valores = dotenv_values(REPO_ROOT / "REDIS" / ".env")
    return valores["REDIS_URL"]


def buscar_ferramentas(mensagem: str, top_k: int = 3, limiar_distancia: float = 0.75) -> list[dict]:
    """limiar_distancia: cosine distance (0 = identico, 2 = oposto). Um
    resultado com distancia acima do limiar e descartado -- e o caso de
    "oi" (zero candidatos), ver entendendno.md.

    0.75 calibrado empiricamente com o catalogo real (4 ferramentas,
    modelo all-MiniLM-L6-v2): perguntas relevantes ficaram entre 0.32-0.66
    de distancia do tool.json certo, "oi" (irrelevante) ficou em 0.82+ pra
    todas as 4 ferramentas -- 0.75 separa os dois grupos com folga. Precisa
    recalibrar se o catalogo crescer muito ou description mudar de estilo."""
    vectorizer = HFTextVectorizer(model="sentence-transformers/all-MiniLM-L6-v2")
    index = SearchIndex.from_dict(SCHEMA, redis_url=_redis_url())

    vetor = vectorizer.embed(mensagem, as_buffer=True)
    query = VectorQuery(
        vector=vetor, vector_field_name="embedding", num_results=top_k,
        return_fields=["name", "plataforma", "description", "tool_json_path", "vector_distance"],
    )
    resultados = index.query(query)

    candidatos = []
    for r in resultados:
        distancia = float(r["vector_distance"])
        if distancia > limiar_distancia:
            continue
        tool_json = json.loads((REPO_ROOT / r["tool_json_path"]).read_text(encoding="utf-8"))
        candidatos.append({**tool_json, "_distancia": round(distancia, 4)})
    return candidatos


if __name__ == "__main__":
    mensagem_arg = sys.argv[1] if len(sys.argv) > 1 else "oi"
    top_k_arg = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    limiar_arg = float(sys.argv[3]) if len(sys.argv) > 3 else 0.75
    print(json.dumps(buscar_ferramentas(mensagem_arg, top_k_arg, limiar_arg), ensure_ascii=False, indent=2))
