"""Fase D do esquema de analise de vendas (parcial): crawlability/
indexacao via Search Console. Ver
docs/superpowers/specs/2026-07-22-esquema-analise-vendas-design.md.

Core Web Vitals (a outra metade da Fase D) fica de fora aqui de proposito
-- depende de chrome-devtools-mcp/Lighthouse rodando o navegador de
verdade, que nao e uma chamada de API. Ver analise_tecnica.py pro aviso
de bloqueio.

Calculo puro -- recebe o retorno cru de sitemaps().list(), devolve saude
agregada.
"""


def calcular_saude_sitemaps(resposta_sitemaps: dict) -> dict:
    sitemaps = resposta_sitemaps.get("sitemap", [])
    resultado = []
    total_submetido = total_indexado = 0

    for sm in sitemaps:
        conteudos = sm.get("contents", [{}])
        submetido = sum(int(c.get("submitted", 0)) for c in conteudos)
        indexado = sum(int(c.get("indexed", 0)) for c in conteudos)
        total_submetido += submetido
        total_indexado += indexado
        resultado.append({
            "path": sm["path"],
            "submetido": submetido,
            "indexado": indexado,
            "taxa_indexacao": round(indexado / submetido, 4) if submetido else None,
            "erros": int(sm.get("errors", 0)),
            "avisos": int(sm.get("warnings", 0)),
            "ultimo_download": sm.get("lastDownloaded"),
        })

    return {
        "sitemaps": resultado,
        "total_submetido": total_submetido,
        "total_indexado": total_indexado,
        "taxa_indexacao_geral": (
            round(total_indexado / total_submetido, 4) if total_submetido else None
        ),
    }
