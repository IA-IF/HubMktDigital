"""Fase C do esquema de analise de vendas: saude do organico (Search
Console). Ver docs/superpowers/specs/2026-07-22-esquema-analise-vendas-design.md.

Calculo puro -- recebe linhas de searchanalytics.query ja buscadas,
devolve o split marca/nao-marca e o CTR/posicao agregados.
"""


def calcular_split_marca(linhas: list[dict], termos_marca: list[str]) -> dict:
    marca = {"clicks": 0, "impressions": 0}
    nao_marca = {"clicks": 0, "impressions": 0}

    for linha in linhas:
        query = linha["query"].lower()
        alvo = marca if any(termo in query for termo in termos_marca) else nao_marca
        alvo["clicks"] += linha["clicks"]
        alvo["impressions"] += linha["impressions"]

    total_clicks = marca["clicks"] + nao_marca["clicks"]

    def _com_percentual(grupo):
        pct = round(grupo["clicks"] / total_clicks, 4) if total_clicks else None
        return {**grupo, "pct_clicks": pct}

    return {"marca": _com_percentual(marca), "nao_marca": _com_percentual(nao_marca)}


def calcular_resumo_organico(linhas: list[dict]) -> dict:
    total_clicks = sum(l["clicks"] for l in linhas)
    total_impressions = sum(l["impressions"] for l in linhas)
    # posicao media ponderada por impressao (senao query rara com posicao
    # ruim pesa igual a uma query de alto volume)
    soma_posicao_ponderada = sum(l["position"] * l["impressions"] for l in linhas)

    return {
        "total_clicks": total_clicks,
        "total_impressions": total_impressions,
        "ctr_medio": round(total_clicks / total_impressions, 4) if total_impressions else None,
        "posicao_media": (
            round(soma_posicao_ponderada / total_impressions, 2) if total_impressions else None
        ),
        "total_queries": len(linhas),
    }
