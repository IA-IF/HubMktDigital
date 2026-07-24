"""Registra pedidos que o Julio ainda nao sabe atender, em vez de inventar.

Quando o usuario pede algo fora das ferramentas disponiveis (nem
`consultar_trafego` nem `propor_campanha` servem), a regra e: nao alucinar
uma resposta nem fingir que fez algo — anotar o pedido aqui pra virar
trabalho futuro, revisado junto (usuario + Claude Code), nao implementado
automaticamente.

Escreve em config.PEDIDOS_FUTUROS (ver julio_config.py).
"""
from datetime import datetime

import julio_config as config

CABECALHO = (
    "# Pedidos futuros do Julio\n\n"
    "Coisas que o usuario pediu e o Julio ainda nao sabe fazer — registradas "
    "automaticamente pela ferramenta `registrar_pedido_futuro` em vez de "
    "inventar uma resposta. Revisar aqui e decidir juntos o que vira "
    "implementacao (nao e uma fila que se implementa sozinha).\n\n"
)


def registrar(site: str, pedido: str, contexto: str = "") -> dict:
    arquivo = config.PEDIDOS_FUTUROS
    if not arquivo.exists():
        arquivo.write_text(CABECALHO, encoding="utf-8")

    agora = datetime.now().strftime("%Y-%m-%d %H:%M")
    nome_site = config.SITE_NOMES.get(site, site)
    linhas = [f"## {agora} — {nome_site}", f"**Pedido:** {pedido}"]
    if contexto:
        linhas.append(f"**Contexto:** {contexto}")
    linhas.append("")

    with arquivo.open("a", encoding="utf-8") as f:
        f.write("\n".join(linhas) + "\n")

    return {"status": "registrado", "arquivo": str(arquivo)}
