"""Assembly do nucleo v2 -- liga Canal real (Telegram), Redis real,
tools reais (TOOLS/**/tool.json) e o cliente Anthropic real. So roda o
loop de long-polling quando executado diretamente (nunca ao importar),
pra nunca competir sem querer com outro consumidor do mesmo token de
bot nem mandar mensagem indesejada a um chat real por acidente.

Credenciais vem de REDIS/.env (mesmo arquivo que AGENTES/julio ja usa
-- nao duplicado, so lido de novo aqui, sem importar codigo de
AGENTES/julio).

Uso:
    python -m ARQUITETURA.nucleo.main <site>
    python -m ARQUITETURA.nucleo.main 3gfoods
"""
import json
import sys
from pathlib import Path

import anthropic
import redis
from dotenv import dotenv_values

from ARQUITETURA.nucleo.agente import processar_turno, resolver_pendencia
from ARQUITETURA.nucleo.canal_telegram import CanalTelegram
from ARQUITETURA.nucleo.execucao import DespachanteConcorrente
from ARQUITETURA.nucleo.executor_tools import criar_executor_tool
from ARQUITETURA.nucleo.memoria import (
    RepositorioEstadoRedis,
    carregar_resumo,
    montar_system_com_resumo,
)

HUB_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = HUB_ROOT / "REDIS" / ".env"

SYSTEM_BASE = (
    "Voce e um agente de marketing digital. Ajuda a criar campanhas de "
    "Google Ads de fato otimizadas que gerem conversao -- esse e o "
    "objetivo do projeto (ver ARQUITETURA/entendimento.md)."
)

MODELO_PADRAO = "claude-sonnet-4-6"


def catalogar_tools() -> list[dict]:
    """Le TOOLS/**/tool.json direto -- leitura pura de arquivo, sem
    depender de AGENTES/julio/discover_tool.py (busca vetorial fica pra
    quando o catalogo crescer o bastante pra precisar filtrar)."""
    return [
        json.loads(caminho.read_text(encoding="utf-8"))
        for caminho in sorted((HUB_ROOT / "TOOLS").glob("**/tool.json"))
    ]


def montar_dependencias(site: str):
    env = dotenv_values(ENV_FILE)
    for obrigatoria in ("ANTHROPIC_API_KEY", "TELEGRAM_BOT_TOKEN", "REDIS_URL"):
        if not env.get(obrigatoria):
            raise SystemExit(f"Variavel {obrigatoria} nao definida em {ENV_FILE}")

    autorizados = {c.strip() for c in env.get("TELEGRAM_AUTHORIZED_CHAT_IDS", "").split(",") if c.strip()}
    canal = CanalTelegram(token=env["TELEGRAM_BOT_TOKEN"])
    cliente_redis = redis.Redis.from_url(env["REDIS_URL"], decode_responses=True)
    repositorio = RepositorioEstadoRedis(cliente_redis)
    cliente_anthropic = anthropic.Anthropic(api_key=env["ANTHROPIC_API_KEY"])
    tools = catalogar_tools()
    tool_por_nome = {t["name"]: t for t in tools}
    executar_tool = criar_executor_tool(HUB_ROOT, tool_por_nome, site)
    despachante = DespachanteConcorrente(max_workers=8)
    modelo = env.get("CLAUDE_MODEL", MODELO_PADRAO)

    return autorizados, canal, cliente_redis, repositorio, cliente_anthropic, tools, executar_tool, despachante, modelo


def processar_mensagem(
    chat_id: str, texto: str, cliente_redis, repositorio, cliente_anthropic,
    tools, executar_tool, canal, modelo: str,
) -> None:
    estado = repositorio.carregar(chat_id)
    resumo = carregar_resumo(cliente_redis, chat_id)
    system = montar_system_com_resumo(SYSTEM_BASE, resumo)

    resposta_baixa = texto.strip().lower()
    if estado.pendente is not None and resposta_baixa in ("sim", "s", "nao", "n"):
        resolver_pendencia(
            cliente_anthropic, modelo, system, tools, estado,
            confirmou=resposta_baixa in ("sim", "s"),
            executar_tool=executar_tool, destinatario=chat_id, canal=canal,
        )
    else:
        processar_turno(
            cliente_anthropic, modelo, system, tools, estado, texto,
            executar_tool=executar_tool, destinatario=chat_id, canal=canal,
        )
    repositorio.salvar(chat_id, estado)


def rodar(site: str) -> None:
    autorizados, canal, cliente_redis, repositorio, cliente_anthropic, tools, executar_tool, despachante, modelo = (
        montar_dependencias(site)
    )
    if not autorizados:
        raise SystemExit("TELEGRAM_AUTHORIZED_CHAT_IDS vazio em REDIS/.env -- defina ao menos um chat_id.")

    print(f"Nucleo v2 rodando pro site '{site}'. Chats autorizados: {autorizados}")
    offset = None
    while True:
        atualizacoes = canal.receber_atualizacoes(offset)
        for atualizacao in atualizacoes:
            offset = atualizacao["update_id"] + 1
            mensagem = atualizacao.get("message")
            if not mensagem or "text" not in mensagem:
                continue
            chat_id = str(mensagem["chat"]["id"])
            if chat_id not in autorizados:
                canal.enviar(chat_id, "Voce nao esta autorizado a usar este bot.")
                continue
            texto = mensagem["text"]
            despachante.despachar(
                chat_id,
                lambda cid=chat_id, txt=texto: processar_mensagem(
                    cid, txt, cliente_redis, repositorio, cliente_anthropic,
                    tools, executar_tool, canal, modelo,
                ),
            )


if __name__ == "__main__":
    site_escolhido = sys.argv[1] if len(sys.argv) > 1 else "3gfoods"
    rodar(site_escolhido)
