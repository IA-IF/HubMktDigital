"""Tool de catalogo de produtos: le o sitemap publico do site (nao o
codigo-fonte) e devolve as URLs de produto -- funciona igual pra
qualquer stack, inclusive o 3G Foods (cujo sitemap hoje e ruim: o
catalogo sai parcial, nao trava).

Uso:
    python catalogo_produtos.py [site]
    python catalogo_produtos.py 3gfoods

Credenciais/config so da raiz do projeto (SITES/<site>/.env).
"""
import json
import sys
from pathlib import Path

from dotenv import dotenv_values

sys.path.insert(0, str(Path(__file__).resolve().parent))

from coleta import buscar_todas_urls
from filtro import filtrar_produtos

REPO_ROOT = Path(__file__).resolve().parents[3]  # TOOLS/CATALOGO/catalogo_produtos -> raiz do projeto


def _site_url(site: str) -> str:
    do_site = dotenv_values(REPO_ROOT / "SITES" / site / ".env")
    if "SITE_URL" not in do_site or not do_site["SITE_URL"]:
        raise SystemExit(
            f"Site '{site}' nao tem SITE_URL configurado — confirme que "
            f"SITES/{site}/.env existe e tem essa variavel."
        )
    return do_site["SITE_URL"].rstrip("/")


def rodar_catalogo(site: str) -> dict:
    sitemap_url = f"{_site_url(site)}/sitemap.xml"
    todas_urls = buscar_todas_urls(sitemap_url)
    produtos = filtrar_produtos(todas_urls, site)

    return {
        "site": site,
        "sitemap_url": sitemap_url,
        "total_urls_sitemap": len(todas_urls),
        "total_produtos": len(produtos),
        "produtos": produtos,
    }


if __name__ == "__main__":
    site_arg = sys.argv[1] if len(sys.argv) > 1 else "3gfoods"
    print(json.dumps(rodar_catalogo(site_arg), ensure_ascii=False, indent=2))
