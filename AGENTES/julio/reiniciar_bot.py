"""Reinicia o main_telegram.py depois de um pedido aplicado
(pedidos_projeto.aplicar), com rollback automatico se o bot nao voltar a
responder.

Roda como PROCESSO SEPARADO (setsid nohup, disparado por
pedidos_projeto.aplicar) -- de proposito, porque precisa matar o
processo do bot que o chamou e sobreviver a isso. Uso:

    python reiniciar_bot.py <pedido_id> <commit_anterior>
"""
import json
import subprocess
import sys
import time
from pathlib import Path

import bot_processo

PACKAGE_ROOT = Path(__file__).resolve().parent
HUB_ROOT = PACKAGE_ROOT.parent.parent
DATA_DIR = PACKAGE_ROOT / "data"

SEGUNDOS_ESPERA_SUBIDA = 12


def _atualizar_status(pedido_id: str, status: str) -> None:
    caminho = DATA_DIR / "pedidos_projeto" / f"{pedido_id}.json"
    registro = json.loads(caminho.read_text(encoding="utf-8"))
    registro["status"] = status
    caminho.write_text(json.dumps(registro, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    pedido_id, commit_anterior = sys.argv[1], sys.argv[2]

    bot_processo.matar_bot()
    time.sleep(2)
    bot_processo.subir_bot()
    time.sleep(SEGUNDOS_ESPERA_SUBIDA)

    if bot_processo.bot_vivo():
        _atualizar_status(pedido_id, "aplicado")
        return

    # Rollback: o merge deixou o bot incapaz de subir -- desfaz e sobe de
    # novo com o codigo anterior, conhecido bom.
    subprocess.run(["git", "reset", "--hard", commit_anterior], cwd=HUB_ROOT)
    bot_processo.matar_bot()
    time.sleep(1)
    bot_processo.subir_bot()
    time.sleep(SEGUNDOS_ESPERA_SUBIDA)

    if bot_processo.bot_vivo():
        _atualizar_status(pedido_id, "erro_aplicar_revertido")
    else:
        _atualizar_status(pedido_id, "erro_critico_bot_parado")


if __name__ == "__main__":
    main()
