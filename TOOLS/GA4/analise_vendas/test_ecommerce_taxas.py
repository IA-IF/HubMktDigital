from ecommerce_taxas import calcular_taxas_ecommerce


def test_calcular_taxas_ecommerce_com_dado_normal():
    dados = {
        "items_viewed": 500,
        "add_to_carts": 80,
        "checkouts": 50,
        "ecommerce_purchases": 35,
        "purchase_revenue": 5250.0,
        "transactions": 35,
    }
    resultado = calcular_taxas_ecommerce(dados)

    assert resultado["add_to_cart_rate"] == 0.16
    assert resultado["checkout_completion_rate"] == 0.7
    assert resultado["aov"] == 150.0


def test_calcular_taxas_ecommerce_com_denominadores_zerados():
    dados = {
        "items_viewed": 0, "add_to_carts": 0, "checkouts": 0,
        "ecommerce_purchases": 0, "purchase_revenue": 0.0, "transactions": 0,
    }
    resultado = calcular_taxas_ecommerce(dados)

    assert resultado == {
        "add_to_cart_rate": None, "checkout_completion_rate": None, "aov": None,
    }
