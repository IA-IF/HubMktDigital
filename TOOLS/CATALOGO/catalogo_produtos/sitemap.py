"""Calculo puro sobre XML de sitemap ja baixado -- nada aqui fala com a
rede (isso fica em coleta.py). Sitemaps seguem o protocolo sitemaps.org:
ou um <urlset> com paginas, ou um <sitemapindex> apontando pra outros
sitemaps (comum em catalogos grandes, paginados por categoria).
"""
import xml.etree.ElementTree as ET

_NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"


def eh_indice(xml_texto: str) -> bool:
    raiz = ET.fromstring(xml_texto)
    return raiz.tag == f"{_NS}sitemapindex"


def extrair_urls(xml_texto: str) -> list[str]:
    """Extrai as <loc> de um <urlset> (paginas de verdade)."""
    raiz = ET.fromstring(xml_texto)
    return [loc.text.strip() for loc in raiz.findall(f".//{_NS}loc") if loc.text]


def extrair_sub_sitemaps(xml_texto: str) -> list[str]:
    """Extrai as <loc> de um <sitemapindex> (urls de outros sitemaps)."""
    return extrair_urls(xml_texto)
