"""Planejador: quebra um pedido em texto numa lista ordenada de tarefas,
gravada no Redis (RedisJSON) pro Coder consumir.
"""
import json
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "llm_router"))
from router import LLMRouter  # noqa: E402

SYSTEM_PROMPT = (
    "Voce e um planejador de tarefas de programacao. Dado um pedido, "
    "quebre em uma lista ordenada de tarefas pequenas e objetivas. "
    "Responda APENAS com JSON valido: uma lista de objetos com os campos "
    '"descricao" (string, o que fazer) e "arquivo" (string, caminho '
    "relativo do arquivo a criar ou alterar). Nao inclua nenhum texto "
    "fora do JSON, nem marcacao de bloco de codigo (```)."
)


class Planejador:
    def __init__(self):
        self.router = LLMRouter()

    def planejar(self, pedido: str) -> dict:
        resposta = self.router.ask(
            pedido, system=SYSTEM_PROMPT, complexity="complex"
        )
        tarefas_brutas = self._parsear_com_retry(pedido, resposta)

        tarefas = [
            {
                "id": i + 1,
                "descricao": t["descricao"],
                "arquivo": t["arquivo"],
                "status": "pendente",
            }
            for i, t in enumerate(tarefas_brutas)
        ]
        plano_id = str(uuid.uuid4())
        plano = {"pedido": pedido, "tarefas": tarefas}

        self.router.redis_client.json().set(f"plan:{plano_id}", "$", plano)

        return {"plano_id": plano_id, **plano}

    def _parsear_com_retry(self, pedido: str, resposta: str) -> list[dict]:
        try:
            return json.loads(resposta)
        except json.JSONDecodeError as e:
            pedido_correcao = (
                f"{pedido}\n\nSua resposta anterior nao era JSON valido "
                f"(erro: {e}). Responda de novo, APENAS com o JSON, sem "
                "texto extra nem marcacao de bloco de codigo."
            )
            resposta2 = self.router.ask(
                pedido_correcao, system=SYSTEM_PROMPT, complexity="complex"
            )
            return json.loads(resposta2)
