"""Executa as tools reais catalogadas em TOOLS/**/tool.json como
subprocesso — generico, guiado pelo metadado de cada tool ("script",
"modo_entrada"), nao por um if/elif por nome. Adicionar uma tool nova
(novo tool.json em TOOLS/) nao exige tocar neste arquivo.

Cada tool e um processo Python independente com seu proprio sys.path (os
modulos irmaos de cada tool, tipo coleta.py, tem nomes repetidos entre
tools diferentes -- import em processo unico colidiria no sys.modules).
A fronteira e sempre: roda o script com o SITE como argv[1], os demais
parametros conforme "modo_entrada" (ver rodar_tool), le JSON do stdout.
"""
import json
import subprocess
import sys

import julio_config as config

HUB_ROOT = config.HUB_ROOT


def _rodar(script, argv: list[str], entrada_stdin: str | None = None) -> dict:
    resultado = subprocess.run(
        [sys.executable, str(script), *argv],
        input=entrada_stdin,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    saida = (resultado.stdout or "").strip()
    try:
        return json.loads(saida)
    except json.JSONDecodeError:
        raise RuntimeError(
            f"{script.name} nao retornou JSON valido (codigo {resultado.returncode}): "
            f"{resultado.stdout}\n{resultado.stderr}"
        )


def rodar_tool(tool: dict, site: str, params: dict) -> dict:
    """Roda a tool descrita por `tool` (registro vindo de discover_tool,
    com campos "script" e "modo_entrada") pro `site`, com os `params` que
    o LLM decidiu passar (ja validados contra o input_schema da tool).

    modo_entrada:
      - "argv": site + cada propriedade do input_schema, NA ORDEM em que
        aparecem no schema, vira argv posicional (listas viram string
        separada por virgula). Propriedades omitidas pelo LLM ficam de
        fora do argv (o script assume o default dele) -- por isso, se o
        LLM pular uma propriedade do meio e preencher uma depois dela,
        o alinhamento posicional quebra; nenhuma tool hoje faz isso na
        pratica (ver spec 2026-07-23-tool-json-cobertura-completa.md).
      - "stdin": so site vai por argv; os `params` inteiros viram um
        JSON no stdin (usado por tools com schema grande/aninhado, tipo
        criar_campanha).
    """
    script = HUB_ROOT / tool["script"]
    modo = tool.get("modo_entrada", "argv")

    if modo == "stdin":
        return _rodar(script, [site], entrada_stdin=json.dumps(params, ensure_ascii=False))

    argv = [site]
    for chave in tool["input_schema"]["properties"]:
        if chave not in params or params[chave] is None:
            break
        valor = params[chave]
        argv.append(",".join(valor) if isinstance(valor, list) else str(valor))
    return _rodar(script, argv)


class PropostaInvalida(RuntimeError):
    """Proposta rejeitada pela validacao PROPRIA da tool (ex: titulo do
    anuncio acima do limite de caracteres do Google Ads) -- mensagem
    sempre limpa e acionavel, seguro mostrar direto ao usuario (diferente
    de uma excecao inesperada, que pode carregar traceback tecnico)."""


def criar_campanha_ads(tool: dict, proposta: dict, site: str) -> dict:
    """Cria a campanha de verdade no Google Ads (sempre PAUSADA).

    Levanta PropostaInvalida se a VALIDACAO falhar (mensagem segura pro
    usuario) ou RuntimeError se a criacao em si falhar por outro motivo
    (pode conter detalhe tecnico -- quem chama decide o que contar ao
    usuario, mas nao deve mostrar direto).
    """
    resposta = rodar_tool(tool, site, proposta)
    if not resposta.get("ok"):
        erros = resposta.get("erros")
        if erros:
            raise PropostaInvalida("; ".join(erros))
        raise RuntimeError(resposta.get("erro", "erro desconhecido"))
    return resposta
