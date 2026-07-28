import textwrap

import pytest

from ARQUITETURA.nucleo.agente import FalhaPermanente, FalhaTransitoria
from ARQUITETURA.nucleo.executor_tools import criar_executor_tool


def _escrever_script(tmp_path, nome: str, codigo: str):
    caminho = tmp_path / nome
    caminho.write_text(textwrap.dedent(codigo), encoding="utf-8")
    return caminho


def test_executor_roda_tool_modo_argv_e_devolve_resultado(tmp_path):
    _escrever_script(tmp_path, "echo_argv.py", """
        import json, sys
        site = sys.argv[1]
        valor = sys.argv[2] if len(sys.argv) > 2 else None
        print(json.dumps({"site": site, "valor": valor}))
    """)
    tool_por_nome = {
        "minha_tool": {
            "script": "echo_argv.py",
            "modo_entrada": "argv",
            "input_schema": {"properties": {"valor": {"type": "string"}}},
        }
    }
    executar = criar_executor_tool(tmp_path, tool_por_nome, "3gfoods")
    resultado = executar("minha_tool", {"valor": "abc"})
    assert resultado == {"site": "3gfoods", "valor": "abc"}


def test_executor_roda_tool_modo_stdin_e_devolve_resultado(tmp_path):
    _escrever_script(tmp_path, "echo_stdin.py", """
        import json, sys
        entrada = json.load(sys.stdin)
        print(json.dumps({"recebido": entrada, "site": sys.argv[1]}))
    """)
    tool_por_nome = {
        "cria_campanha": {
            "script": "echo_stdin.py",
            "modo_entrada": "stdin",
            "input_schema": {"properties": {}},
        }
    }
    executar = criar_executor_tool(tmp_path, tool_por_nome, "adoro")
    resultado = executar("cria_campanha", {"nome": "X"})
    assert resultado == {"recebido": {"nome": "X"}, "site": "adoro"}


def test_executor_levanta_falha_permanente_quando_ok_false_com_erros(tmp_path):
    _escrever_script(tmp_path, "falha_validacao.py", """
        import json
        print(json.dumps({"ok": False, "erros": ["titulo excede 30 caracteres"]}))
    """)
    tool_por_nome = {"t": {"script": "falha_validacao.py", "modo_entrada": "argv", "input_schema": {"properties": {}}}}
    executar = criar_executor_tool(tmp_path, tool_por_nome, "3gfoods")
    with pytest.raises(FalhaPermanente, match="titulo excede 30 caracteres"):
        executar("t", {})


def test_executor_levanta_falha_transitoria_quando_saida_nao_e_json(tmp_path):
    _escrever_script(tmp_path, "quebra.py", """
        raise ModuleNotFoundError("No module named 'google'")
    """)
    tool_por_nome = {"t": {"script": "quebra.py", "modo_entrada": "argv", "input_schema": {"properties": {}}}}
    executar = criar_executor_tool(tmp_path, tool_por_nome, "3gfoods")
    with pytest.raises(FalhaTransitoria):
        executar("t", {})


def test_executor_levanta_falha_permanente_pra_tool_desconhecida(tmp_path):
    executar = criar_executor_tool(tmp_path, {}, "3gfoods")
    with pytest.raises(FalhaPermanente, match="desconhecida"):
        executar("nao_existe", {})
