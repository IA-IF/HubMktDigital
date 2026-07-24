from filtro import filtrar_produtos

URLS_EXEMPLO = [
    "https://site.com/produto/whey-protein",
    "https://site.com/categoria/proteinas",
    "https://site.com/sobre-nos",
    "https://site.com/product/barra-proteica",
]


def test_filtrar_produtos_mantem_so_urls_de_produto():
    assert filtrar_produtos(URLS_EXEMPLO, "integrafoods") == [
        "https://site.com/produto/whey-protein",
        "https://site.com/product/barra-proteica",
    ]


def test_filtrar_produtos_site_sem_padrao_customizado_usa_padrao_geral():
    assert filtrar_produtos(URLS_EXEMPLO, "site_desconhecido") == [
        "https://site.com/produto/whey-protein",
        "https://site.com/product/barra-proteica",
    ]


def test_filtrar_produtos_sem_match_retorna_vazio():
    assert filtrar_produtos(["https://site.com/blog/post-1"], "adoro") == []
