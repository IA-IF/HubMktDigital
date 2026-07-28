"""Despacho de tools reais catalogadas em TOOLS/**/tool.json --
generaliza AGENTES/julio/agentes.py (rodar_tool/criar_campanha_ads)
falando o vocabulario de falha do nucleo v2 (FalhaPermanente vs
FalhaTransitoria) em vez de RuntimeError generico.
"""
import json
import subprocess
import sys
from pathlib import Path

from ARQUITETURA.nucleo.agente import ExecutorTool, FalhaPermanente, FalhaTransitoria


def _rodar_subprocess(script: Path, argv: list[str], entrada_stdin: str | None = None) -> dict:
    resultado = subprocess.run(
        [sys.executable, str(script), *argv],
        input=entrada_stdin, capture_output=True, text=True, encoding="utf-8",
    )
    saida = (resultado.stdout or "").strip()
    try:
        return json.loads(saida)
    except json.JSONDecodeError:
        raise FalhaTransitoria(
            f"{script.name} nao retornou JSON valido (codigo {resultado.returncode}): "
            f"{resultado.stdout}\n{resultado.stderr}"
        )


def criar_executor_tool(hub_root: Path, tool_por_nome: dict[str, dict], site: str) -> ExecutorTool:
    def executar(nome_tool: str, entrada: dict) -> dict:
        tool = tool_por_nome.get(nome_tool)
        if tool is None:
            raise FalhaPermanente(f"ferramenta desconhecida: {nome_tool}")

        script = hub_root / tool["script"]
        modo = tool.get("modo_entrada", "argv")

        if modo == "stdin":
            resposta = _rodar_subprocess(script, [site], entrada_stdin=json.dumps(entrada, ensure_ascii=False))
        else:
            argv = [site]
            for chave in tool["input_schema"]["properties"]:
                if chave not in entrada or entrada[chave] is None:
                    break
                valor = entrada[chave]
                argv.append(",".join(valor) if isinstance(valor, list) else str(valor))
            resposta = _rodar_subprocess(script, argv)

        if resposta.get("ok") is False and "erros" in resposta:
            raise FalhaPermanente("; ".join(resposta["erros"]))
        return resposta

    return executar
