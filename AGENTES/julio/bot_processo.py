"""Controle do processo do bot (matar/subir/checar vivo) -- extraido de
reiniciar_bot.py pra ser reusado tambem por status_server.py (endpoint
HTTP de start/stop/status na EC2, ver plano
docs/superpowers/plans/2026-07-27-status-controle-bot-ec2.md). Mesma
tecnica de sempre (pkill/pgrep/nohup), nenhum comportamento novo.
"""
import subprocess
import sys
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent
DATA_DIR = PACKAGE_ROOT / "data"


def matar_bot() -> None:
    subprocess.run(["pkill", "-f", "main_telegram.py"])


def subir_bot() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    log = (DATA_DIR / "julio.log").open("a", encoding="utf-8")
    err = (DATA_DIR / "julio.err.log").open("a", encoding="utf-8")
    subprocess.Popen(
        ["setsid", "nohup", sys.executable, "main_telegram.py"],
        cwd=PACKAGE_ROOT, stdout=log, stderr=err, stdin=subprocess.DEVNULL,
        start_new_session=True,
    )


def bot_vivo() -> bool:
    return subprocess.run(["pgrep", "-f", "main_telegram.py"], capture_output=True).returncode == 0
