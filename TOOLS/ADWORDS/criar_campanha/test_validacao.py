from validacao import brl_para_micros, validar_proposta

PROPOSTA_VALIDA = {
    "nome_campanha": "Whey Protein — Julho",
    "orcamento_diario_brl": 50.0,
    "lance_inicial_brl": 2.5,
    "url_final": "https://integrafoods.com.br/produto/whey-protein",
    "palavras_chave": [{"texto": "whey protein"}, {"texto": "proteina em po"}],
    "titulos": ["Whey Protein Integra Foods", "Proteina de qualidade", "Compre agora"],
    "descricoes": ["Proteina isolada premium.", "Entrega rapida em todo o Brasil."],
}


def test_brl_para_micros_converte_corretamente():
    assert brl_para_micros(50.0) == 50_000_000
    assert brl_para_micros(2.5) == 2_500_000


def test_validar_proposta_completa_sem_erros():
    assert validar_proposta(PROPOSTA_VALIDA) == []


def test_validar_proposta_sem_nome_acusa_erro():
    proposta = {**PROPOSTA_VALIDA, "nome_campanha": ""}
    erros = validar_proposta(proposta)
    assert any("nome_campanha" in erro for erro in erros)


def test_validar_proposta_orcamento_negativo_acusa_erro():
    proposta = {**PROPOSTA_VALIDA, "orcamento_diario_brl": -10}
    erros = validar_proposta(proposta)
    assert any("orcamento_diario_brl" in erro for erro in erros)


def test_validar_proposta_url_sem_http_acusa_erro():
    proposta = {**PROPOSTA_VALIDA, "url_final": "integrafoods.com.br/produto"}
    erros = validar_proposta(proposta)
    assert any("url_final" in erro for erro in erros)


def test_validar_proposta_sem_palavras_chave_acusa_erro():
    proposta = {**PROPOSTA_VALIDA, "palavras_chave": []}
    erros = validar_proposta(proposta)
    assert any("palavras_chave" in erro for erro in erros)


def test_validar_proposta_poucos_titulos_acusa_erro():
    proposta = {**PROPOSTA_VALIDA, "titulos": ["Só um titulo"]}
    erros = validar_proposta(proposta)
    assert any("titulos" in erro for erro in erros)


def test_validar_proposta_poucas_descricoes_acusa_erro():
    proposta = {**PROPOSTA_VALIDA, "descricoes": ["So uma descricao"]}
    erros = validar_proposta(proposta)
    assert any("descricoes" in erro for erro in erros)
