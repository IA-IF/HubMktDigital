"""Split de sessao por canal + taxa de conversao por canal (Fase A do
esquema de analise de vendas). Dado bruto vem de runReport dimensionado
por sessionDefaultChannelGroup (ver TOOLS/GA4/DOCS/raw/metadata_3gfoods.json).
"""


def calcular_split_canal(linhas: list[dict]) -> list[dict]:
    resultado = []
    for linha in linhas:
        sessoes = linha["sessoes"]
        compras = linha["compras"]
        taxa = round(compras / sessoes, 4) if sessoes else None
        resultado.append({**linha, "taxa_conversao": taxa})
    return sorted(resultado, key=lambda r: r["sessoes"], reverse=True)
