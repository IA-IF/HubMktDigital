"""Taxas de ecommerce (Fase A do esquema de analise de vendas): add-to-cart
rate, checkout completion rate, AOV. Formulas e benchmarks documentados em
docs/superpowers/specs/2026-07-22-esquema-analise-vendas-design.md
(add-to-cart >=12% e checkout completion >=70% sao os benchmarks de
mercado citados na spec, nao um valor fixo do codigo).
"""


def calcular_taxas_ecommerce(dados: dict) -> dict:
    items_viewed = dados["items_viewed"]
    checkouts = dados["checkouts"]
    transactions = dados["transactions"]

    add_to_cart_rate = round(dados["add_to_carts"] / items_viewed, 4) if items_viewed else None
    checkout_completion_rate = (
        round(dados["ecommerce_purchases"] / checkouts, 4) if checkouts else None
    )
    aov = round(dados["purchase_revenue"] / transactions, 2) if transactions else None

    return {
        "add_to_cart_rate": add_to_cart_rate,
        "checkout_completion_rate": checkout_completion_rate,
        "aov": aov,
    }
