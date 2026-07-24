"""Busca o sitemap real via HTTP pra alimentar sitemap.py/filtro.py.
Unica peca deste modulo que fala com a rede de verdade -- sem teste
automatizado, mesma logica de TOOLS/GA4/analise_vendas/coleta.py (a
logica de parse/filtro ja foi testada nas pecas puras).
"""
import requests

from sitemap import eh_indice, extrair_sub_sitemaps, extrair_urls

TIMEOUT_SEGUNDOS = 15


def _baixar(url: str) -> str:
    resp = requests.get(url, timeout=TIMEOUT_SEGUNDOS, headers={"User-Agent": "HubMktDigital-catalogo/1.0"})
    resp.raise_for_status()
    return resp.text


def buscar_todas_urls(sitemap_url: str) -> list[str]:
    """Baixa o sitemap raiz; se for um indice, baixa cada sub-sitemap e
    junta tudo. Um sub-sitemap que falhar (404, timeout) e ignorado --
    o catalogo sai parcial em vez de travar por causa de uma categoria.
    """
    xml_raiz = _baixar(sitemap_url)
    if not eh_indice(xml_raiz):
        return extrair_urls(xml_raiz)

    todas_urls = []
    for sub_url in extrair_sub_sitemaps(xml_raiz):
        try:
            todas_urls.extend(extrair_urls(_baixar(sub_url)))
        except requests.RequestException:
            continue
    return todas_urls
