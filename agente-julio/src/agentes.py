"""Chama os outros agentes (agente-ads, e no futuro agente-gtm/ga4/search-console).

Cada agente e um processo Python independente com seu proprio .env.<site> e
dependencias — o Julio nao importa o codigo deles diretamente (evitaria um
conflito de pacote "src" entre modulos irmaos) nem precisa saber como cada um
funciona por dentro. A fronteira e sempre: roda `main.py` do agente com o
mesmo SITE, manda JSON pro stdin quando precisa, le JSON do stdout.
"""
import json
import subprocess
import sys

from src import config


def criar_campanha_ads(proposta: dict, site: str) -> dict:
    """Pede ao agente-ads para criar a campanha (sempre PAUSADA).

    Levanta RuntimeError com a mensagem de erro do agente-ads se a criacao
    falhar (credenciais invalidas, API do Google Ads recusando algo, etc.).
    """
    resultado = subprocess.run(
        [sys.executable, str(config.AGENTE_ADS_MAIN), "--criar-campanha"],
        input=json.dumps(proposta, ensure_ascii=False),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={"SITE": site, **_env_sem_site()},
    )

    saida = (resultado.stdout or "").strip().splitlines()
    ultima_linha = saida[-1] if saida else ""
    try:
        resposta = json.loads(ultima_linha)
    except json.JSONDecodeError:
        raise RuntimeError(
            f"agente-ads nao retornou JSON valido (codigo {resultado.returncode}): "
            f"{resultado.stdout}\n{resultado.stderr}"
        )

    if not resposta.get("ok"):
        raise RuntimeError(resposta.get("erro", "erro desconhecido no agente-ads"))
    return resposta


def consultar_trafego_ga4(site: str, dias: int = 7) -> dict:
    """Pede ao agente-ga4 um resumo de trafego + ecommerce por canal (so leitura).

    Levanta RuntimeError se o agente-ga4 falhar (credenciais, propriedade
    sem dado no periodo, etc.) — quem chama decide o que fazer (normalmente:
    contar isso pro LLM como resultado da tool, nao derrubar a conversa).
    """
    resultado = subprocess.run(
        [sys.executable, str(config.AGENTE_GA4_MAIN), "--trafego", "--dias", str(dias)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={"SITE": site, **_env_sem_site()},
    )

    saida = (resultado.stdout or "").strip().splitlines()
    ultima_linha = saida[-1] if saida else ""
    try:
        return json.loads(ultima_linha)
    except json.JSONDecodeError:
        raise RuntimeError(
            f"agente-ga4 nao retornou JSON valido (codigo {resultado.returncode}): "
            f"{resultado.stdout}\n{resultado.stderr}"
        )


def _env_sem_site() -> dict:
    import os
    return {k: v for k, v in os.environ.items() if k != "SITE"}
