"""Contrato único de validação/reparo entre "o que o LLM decidiu
chamar" (tool_use.input) e "o que vai executar de verdade". A API da
Anthropic usa o input_schema de uma tool só como sugestão pro modelo --
não garante nem tipo nem campo obrigatório. Isso generaliza os fixes ad
hoc feitos em AGENTES/julio/orchestrator.py (_corrigir_tipos_input/
_validar_input_schema) numa peça reutilizável por qualquer chamador.
"""
import json

_TIPO_JSON_PARA_PYTHON = {
    "string": str,
    "number": (int, float),
    "integer": int,
    "array": list,
    "object": dict,
    "boolean": bool,
}


class InputInvalido(Exception):
    def __init__(self, problemas: list[str]):
        super().__init__("; ".join(problemas))
        self.problemas = problemas


def corrigir_tipos_input(entrada: dict, schema: dict) -> dict:
    """Alguns modelos serializam um campo array/object em DUAS camadas
    -- mandam a string JSON em vez da lista/objeto de verdade. Tenta
    desserializar antes de validar; se não for JSON válido, mantém
    como veio (a validação de tipo abaixo vai pegar isso)."""
    propriedades = schema.get("properties", {})
    corrigido = dict(entrada)
    for campo, valor in entrada.items():
        esperado = propriedades.get(campo, {}).get("type")
        if esperado in ("array", "object") and isinstance(valor, str):
            try:
                corrigido[campo] = json.loads(valor)
            except json.JSONDecodeError:
                pass
    return corrigido


def validar_input_schema(entrada: dict, schema: dict) -> list[str]:
    """Validação mínima e genérica: campo obrigatório presente e tipo
    Python bate com o `type` declarado no schema."""
    propriedades = schema.get("properties", {})
    problemas = []
    for campo in schema.get("required", []):
        if campo not in entrada or entrada[campo] in (None, "", []):
            problemas.append(f"{campo}: obrigatorio e ausente")
            continue
        tipo_esperado = _TIPO_JSON_PARA_PYTHON.get(propriedades.get(campo, {}).get("type"))
        if tipo_esperado and not isinstance(entrada[campo], tipo_esperado):
            problemas.append(
                f"{campo}: deveria ser {propriedades[campo]['type']}, "
                f"veio {type(entrada[campo]).__name__} ({entrada[campo]!r})"
            )
    return problemas


def preparar_input(entrada: dict, schema: dict) -> dict:
    """Corrige tipos e valida contra o schema. Levanta InputInvalido se
    sobrar problema depois da correção; senão devolve o input pronto
    pra uso."""
    corrigido = corrigir_tipos_input(entrada, schema)
    problemas = validar_input_schema(corrigido, schema)
    if problemas:
        raise InputInvalido(problemas)
    return corrigido
