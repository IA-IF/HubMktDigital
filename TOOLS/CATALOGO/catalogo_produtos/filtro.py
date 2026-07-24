"""Calculo puro: separa URLs de produto das demais paginas do sitemap
(categoria, institucional, blog). Padrao por site porque cada loja tem
sua propria estrutura de URL -- ajustar PADROES_PRODUTO conforme os
sitemaps reais forem inspecionados.
"""

PADRAO_PADRAO = ["/produto/", "/product/", "/p/"]

PADROES_PRODUTO = {
    "integrafoods": PADRAO_PADRAO,
    "adoro": PADRAO_PADRAO,
    "3gfoods": PADRAO_PADRAO,
}


def filtrar_produtos(urls: list[str], site: str) -> list[str]:
    padroes = PADROES_PRODUTO.get(site, PADRAO_PADRAO)
    return [
        url for url in urls
        if any(padrao in url.lower() for padrao in padroes)
    ]
