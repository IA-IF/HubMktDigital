from sitemap import eh_indice, extrair_sub_sitemaps, extrair_urls

URLSET_EXEMPLO = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://site.com/produto/whey-protein</loc></url>
  <url><loc>https://site.com/categoria/proteinas</loc></url>
</urlset>"""

INDICE_EXEMPLO = """<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap><loc>https://site.com/sitemap-produtos.xml</loc></sitemap>
  <sitemap><loc>https://site.com/sitemap-categorias.xml</loc></sitemap>
</sitemapindex>"""


def test_eh_indice_reconhece_urlset_como_nao_indice():
    assert eh_indice(URLSET_EXEMPLO) is False


def test_eh_indice_reconhece_sitemapindex():
    assert eh_indice(INDICE_EXEMPLO) is True


def test_extrair_urls_pega_todas_as_loc():
    urls = extrair_urls(URLSET_EXEMPLO)
    assert urls == [
        "https://site.com/produto/whey-protein",
        "https://site.com/categoria/proteinas",
    ]


def test_extrair_sub_sitemaps_pega_urls_dos_sub_sitemaps():
    sub_urls = extrair_sub_sitemaps(INDICE_EXEMPLO)
    assert sub_urls == [
        "https://site.com/sitemap-produtos.xml",
        "https://site.com/sitemap-categorias.xml",
    ]
