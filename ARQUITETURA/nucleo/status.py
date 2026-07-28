"""Texto de /status e controle de processo (subir/matar/checar vivo)
do bot do nucleo v2 -- espelha AGENTES/julio/julio_config.texto_status()
+ AGENTES/julio/bot_processo.py, mas falando do processo
`ARQUITETURA.nucleo.main` (nao main_telegram.py). Duplicado por
proposito, mesma razao de TOOLS/ADWORDS/ads_mutate/mutate.py: cada
parte do projeto e independente, ARQUITETURA nao importa de
AGENTES/julio.
"""
import subprocess
import sys
from pathlib import Path

from dotenv import dotenv_values

HUB_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = HUB_ROOT / "REDIS" / ".env"
DATA_DIR = HUB_ROOT / "data"
PROCESSO = "ARQUITETURA.nucleo.main"


def ambiente() -> str:
    """"EC2" ou "local" -- mesma variavel AMBIENTE de REDIS/.env que o
    bot antigo ja usava, pra separar qual instancia esta respondendo."""
    return (dotenv_values(ENV_FILE).get("AMBIENTE") or "local").strip() or "local"


def texto_status() -> str:
    resultado = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"], cwd=HUB_ROOT,
        capture_output=True, text=True,
    )
    versao = resultado.stdout.strip() if resultado.returncode == 0 else "desconhecida"
    return f"Versao: {versao}\nAmbiente: {ambiente()}\nArquitetura: nucleo v2"


def matar_bot() -> None:
    subprocess.run(["pkill", "-f", PROCESSO])


def subir_bot() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    log = (DATA_DIR / "nucleo.log").open("a", encoding="utf-8")
    err = (DATA_DIR / "nucleo.err.log").open("a", encoding="utf-8")
    subprocess.Popen(
        ["setsid", "nohup", sys.executable, "-m", PROCESSO],
        cwd=HUB_ROOT, stdout=log, stderr=err, stdin=subprocess.DEVNULL,
        start_new_session=True,
    )


def bot_vivo() -> bool:
    return subprocess.run(["pgrep", "-f", PROCESSO], capture_output=True).returncode == 0
