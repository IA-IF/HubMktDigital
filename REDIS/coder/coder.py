"""Coder: gera codigo Python pra uma tarefa, valida sintaxe antes de
escrever, escreve so dentro da raiz deste projeto (nunca nos sites de
producao — guardrail verificado em codigo).
"""
import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "llm_router"))
from router import LLMRouter  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

SYSTEM_PROMPT = (
    "Voce e um agente que escreve codigo Python. Dada uma descricao de "
    "tarefa, responda APENAS com o codigo Python completo do arquivo, "
    "pronto pra salvar direto. Sem explicacao, sem markdown, sem cercas "
    "de bloco de codigo (```)."
)


class Coder:
    def __init__(self):
        self.router = LLMRouter()

    def implementar(self, tarefa: dict) -> dict:
        arquivo_relativo = tarefa["arquivo"]
        caminho = (REPO_ROOT / arquivo_relativo).resolve()

        try:
            caminho.relative_to(REPO_ROOT)
        except ValueError:
            return {
                "arquivo": arquivo_relativo,
                "escrito": False,
                "erro": f"arquivo fora da raiz do projeto: {arquivo_relativo}",
            }

        codigo = self._gerar_codigo(tarefa["descricao"])
        valido, erro = self._validar_sintaxe(codigo)

        if not valido:
            codigo = self._gerar_codigo(
                f"{tarefa['descricao']}\n\nSeu codigo anterior tinha um "
                f"erro de sintaxe: {erro}\nGere o arquivo completo de "
                "novo, corrigido."
            )
            valido, erro = self._validar_sintaxe(codigo)

        if not valido:
            return {"arquivo": arquivo_relativo, "escrito": False, "erro": erro}

        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_text(codigo, encoding="utf-8")
        return {"arquivo": arquivo_relativo, "escrito": True, "erro": None}

    def _gerar_codigo(self, descricao: str) -> str:
        return self.router.ask(
            descricao, system=SYSTEM_PROMPT, complexity="complex"
        )

    @staticmethod
    def _validar_sintaxe(codigo: str) -> tuple[bool, str | None]:
        try:
            ast.parse(codigo)
            return True, None
        except SyntaxError as e:
            return False, str(e)
