import pytest

from ARQUITETURA.nucleo.validacao_tool import (
    InputInvalido,
    corrigir_tipos_input,
    preparar_input,
    validar_input_schema,
)

SCHEMA = {
    "type": "object",
    "properties": {
        "nome": {"type": "string"},
        "orcamento": {"type": "number"},
        "palavras_chave": {"type": "array"},
    },
    "required": ["nome", "orcamento", "palavras_chave"],
}


def test_corrigir_tipos_desserializa_array_vindo_como_string():
    entrada = {"nome": "X", "orcamento": 10, "palavras_chave": '[{"texto": "a"}]'}
    corrigido = corrigir_tipos_input(entrada, SCHEMA)
    assert corrigido["palavras_chave"] == [{"texto": "a"}]


def test_corrigir_tipos_mantem_string_invalida_como_veio():
    entrada = {"nome": "X", "orcamento": 10, "palavras_chave": "nao e json"}
    corrigido = corrigir_tipos_input(entrada, SCHEMA)
    assert corrigido["palavras_chave"] == "nao e json"


def test_corrigir_tipos_nao_muta_entrada_original():
    entrada = {"nome": "X", "orcamento": 10, "palavras_chave": '["a"]'}
    corrigir_tipos_input(entrada, SCHEMA)
    assert entrada["palavras_chave"] == '["a"]'


def test_validar_schema_pega_campo_obrigatorio_ausente():
    entrada = {"nome": "X", "orcamento": 10}
    problemas = validar_input_schema(entrada, SCHEMA)
    assert any("palavras_chave" in p for p in problemas)


def test_validar_schema_pega_tipo_errado():
    entrada = {"nome": "X", "orcamento": "dez", "palavras_chave": ["a"]}
    problemas = validar_input_schema(entrada, SCHEMA)
    assert any("orcamento" in p for p in problemas)


def test_validar_schema_ok_sem_problemas():
    entrada = {"nome": "X", "orcamento": 10, "palavras_chave": ["a"]}
    assert validar_input_schema(entrada, SCHEMA) == []


def test_preparar_input_corrige_e_devolve_quando_valido():
    entrada = {"nome": "X", "orcamento": 10, "palavras_chave": '["a"]'}
    resultado = preparar_input(entrada, SCHEMA)
    assert resultado == {"nome": "X", "orcamento": 10, "palavras_chave": ["a"]}


def test_preparar_input_levanta_quando_invalido():
    entrada = {"orcamento": "dez"}
    with pytest.raises(InputInvalido) as exc_info:
        preparar_input(entrada, SCHEMA)
    problemas = exc_info.value.problemas
    assert any("nome" in p for p in problemas)
    assert any("orcamento" in p for p in problemas)
    assert any("palavras_chave" in p for p in problemas)
