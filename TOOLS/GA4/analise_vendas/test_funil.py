from funil import ETAPAS_FUNIL, calcular_funil


def test_etapas_funil_na_ordem_certa():
    assert ETAPAS_FUNIL == [
        "session_start", "view_item", "add_to_cart", "begin_checkout", "purchase",
    ]


def test_calcular_funil_com_queda_normal():
    contagens = {
        "session_start": 1000,
        "view_item": 400,
        "add_to_cart": 100,
        "begin_checkout": 50,
        "purchase": 20,
    }
    resultado = calcular_funil(contagens)

    assert len(resultado) == 5
    assert resultado[0] == {
        "etapa": "session_start", "contagem": 1000,
        "taxa_retencao": 1.0, "taxa_abandono": 0.0,
    }
    assert resultado[1]["etapa"] == "view_item"
    assert resultado[1]["contagem"] == 400
    assert resultado[1]["taxa_retencao"] == 0.4
    assert resultado[1]["taxa_abandono"] == 0.6
    assert resultado[4]["etapa"] == "purchase"
    assert resultado[4]["taxa_retencao"] == 0.4


def test_calcular_funil_com_etapa_zerada_nao_divide_por_zero():
    contagens = {
        "session_start": 1000,
        "view_item": 0,
        "add_to_cart": 0,
        "begin_checkout": 0,
        "purchase": 0,
    }
    resultado = calcular_funil(contagens)

    assert resultado[1]["taxa_retencao"] is None
    assert resultado[1]["taxa_abandono"] is None


def test_calcular_funil_aceita_contagem_faltando_como_zero():
    contagens = {"session_start": 500}
    resultado = calcular_funil(contagens)

    assert resultado[1]["contagem"] == 0
    assert resultado[1]["taxa_retencao"] == 0.0
