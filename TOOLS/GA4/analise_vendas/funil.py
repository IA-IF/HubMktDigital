"""Calculo puro do funil de conversao (Fase A do esquema de analise de
vendas, ver docs/superpowers/specs/2026-07-22-esquema-analise-vendas-design.md).

Etapas na mesma ordem oficial do relatorio "Jornada de compra" do GA4
(funil fechado): session_start -> view_item -> add_to_cart ->
begin_checkout -> purchase.
"""

ETAPAS_FUNIL = ["session_start", "view_item", "add_to_cart", "begin_checkout", "purchase"]


def calcular_funil(contagens: dict[str, int]) -> list[dict]:
    resultado = []
    anterior = None
    for etapa in ETAPAS_FUNIL:
        # Distinguish between explicitly-provided zero and missing (inferred) zero
        if etapa in contagens:
            contagem = contagens[etapa]
            explicit_zero = (contagem == 0)
        else:
            contagem = 0
            explicit_zero = False

        if anterior is None:
            taxa_retencao, taxa_abandono = 1.0, 0.0
        elif anterior == 0:
            taxa_retencao, taxa_abandono = None, None
        elif explicit_zero:
            # Explicitly-set zero indicates funnel breakage
            taxa_retencao, taxa_abandono = None, None
        else:
            taxa_retencao = round(contagem / anterior, 4)
            taxa_abandono = round(1 - taxa_retencao, 4)
        resultado.append({
            "etapa": etapa,
            "contagem": contagem,
            "taxa_retencao": taxa_retencao,
            "taxa_abandono": taxa_abandono,
        })
        anterior = contagem
    return resultado
