from canais import calcular_split_canal


def test_calcular_split_canal_ordena_por_sessoes_e_calcula_taxa():
    linhas = [
        {"canal": "Organic Search", "sessoes": 200, "compras": 7},
        {"canal": "Paid Search", "sessoes": 500, "compras": 4},
        {"canal": "Direct", "sessoes": 100, "compras": 1},
    ]
    resultado = calcular_split_canal(linhas)

    assert [r["canal"] for r in resultado] == ["Paid Search", "Organic Search", "Direct"]
    assert resultado[0]["taxa_conversao"] == 0.008
    assert resultado[1]["taxa_conversao"] == 0.035
    assert resultado[2]["taxa_conversao"] == 0.01


def test_calcular_split_canal_com_zero_sessoes_nao_divide_por_zero():
    linhas = [{"canal": "Referral", "sessoes": 0, "compras": 0}]
    resultado = calcular_split_canal(linhas)

    assert resultado[0]["taxa_conversao"] is None
