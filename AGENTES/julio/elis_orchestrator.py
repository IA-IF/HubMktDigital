"""A Elis: agente de conversa dedicado a EVOLUIR O PROPRIO PROJETO
HubMktDigital -- irma do Julio (orchestrator.py, que cuida so de
marketing de site). So um dos dois fica ativo por vez no bot Telegram,
escolhido por AGENTE_ATIVO em REDIS/.env (ver julio_config.agente_ativo,
main_telegram.py).

Sem selecao de site (nao e sobre marketing) -- so conversa sobre o que
o HubMktDigital ja faz/o que falta (contexto: STATUS_PROJETO.md) e, via
pedidos_projeto.py, registra + aplica pedidos de mudanca no proprio
projeto:
  1. `registrar_pedido_projeto` dispara Planejador->Coder numa branch
     git isolada (pedido/<id>), nunca em master.
  2. Com o rascunho pronto, vira confirmacao pendente ("aplicar?").
  3. Um "sim" chama `pedidos_projeto.aplicar`: merge em master + o bot
     se reinicia sozinho (reiniciar_bot.py), com rollback automatico se
     nao voltar a responder.

Estado (so historico + pedido pendente) persiste em
data/conversas_elis/<chat_id>.json.
"""
import json

import anthropic

import julio_config as config
import pedidos_projeto

MAX_TURNOS_FERRAMENTA = 4

SCHEMA_PEDIDO_PROJETO = {
    "type": "object",
    "properties": {
        "pedido": {
            "type": "string",
            "description": "Resumo objetivo do que foi pedido, 1-2 frases.",
        },
        "contexto": {
            "type": "string",
            "description": "Detalhes adicionais relevantes. Opcional.",
        },
    },
    "required": ["pedido"],
}

DESCRICAO_PEDIDO_PROJETO = (
    "Chame quando descreverem algo que querem MUDAR ou ADICIONAR no "
    "projeto -- ex: 'quero que o bot tambem avise sobre X'. Nao chame "
    "so pra responder uma pergunta sobre o que ja existe hoje -- isso "
    "voce ja sabe pelo contexto desta conversa."
)

SCHEMA_LISTAR_PEDIDOS = {"type": "object", "properties": {}, "required": []}

DESCRICAO_LISTAR_PEDIDOS = (
    "Chame quando perguntarem o status de pedidos ja feitos antes (ex: "
    "'como estao meus pedidos', 'o que eu pedi')."
)

_STATUS_PEDIDO_HUMANO = {
    "registrado": "na fila",
    "rascunho_pronto": "rascunho pronto, aguardando confirmacao pra aplicar",
    "aplicando": "aplicando agora",
    "aplicado": "aplicado, ja esta no ar",
    "erro": "registrado, precisa de atencao manual",
    "erro_aplicar": "erro ao aplicar, rascunho preservado pra tentar de novo",
    "erro_aplicar_revertido": "tentei aplicar mas revertido automaticamente por seguranca",
    "erro_critico_bot_parado": "erro critico ao aplicar, precisa de atencao humana urgente",
}


def _sistema() -> str:
    status = config.status_projeto_md().read_text(encoding="utf-8")
    personalidade = config.global_elis_md().read_text(encoding="utf-8")
    return (
        "Voce e a Elis, agente dedicada a evoluir o proprio projeto "
        "HubMktDigital -- nao fala sobre marketing de sites (isso e "
        "trabalho do Julio, outro agente). Conversa com quem esta "
        "gerindo o projeto: explica o que ja existe e o que falta, e "
        "quando pedirem uma mudanca de verdade no projeto, usa "
        "`registrar_pedido_projeto`. Use `listar_pedidos_projeto` "
        "quando perguntarem o status de pedidos ja feitos. Nao "
        "mencione jargao tecnico (branch, commit, git) nas respostas "
        "-- fale em termos simples ('rascunho preparado', 'aplicado'). "
        "REGRA INEGOCIAVEL: nunca finja ter feito algo que nao fez.\n\n"
        f"=== Personalidade ===\n{personalidade}\n\n"
        f"=== Status do projeto (o que ja existe, o que falta) ===\n{status}"
    )


def _perguntar(
    historico: list[dict], chat_id: str, telegram_transport
) -> tuple[str | None, dict | None, list[dict]]:
    """Devolve (bloco_texto, pendencia, novos_turnos). `pendencia`, quando
    presente, e {"tipo": "pedido", "id": ...} -- pedido com rascunho
    pronto, aguardando confirmacao "aplicar? sim/nao"."""
    client = anthropic.Anthropic(api_key=config.anthropic_api_key())
    sistema = _sistema()
    tools = [
        {
            "name": "registrar_pedido_projeto",
            "description": DESCRICAO_PEDIDO_PROJETO,
            "input_schema": SCHEMA_PEDIDO_PROJETO,
        },
        {
            "name": "listar_pedidos_projeto",
            "description": DESCRICAO_LISTAR_PEDIDOS,
            "input_schema": SCHEMA_LISTAR_PEDIDOS,
        },
    ]

    mensagens = list(historico)
    novos_turnos: list[dict] = []

    for _ in range(MAX_TURNOS_FERRAMENTA):
        resposta = client.messages.create(
            model=config.claude_model(), max_tokens=2000,
            system=sistema, tools=tools, messages=mensagens,
        )
        bloco_tool = next((b for b in resposta.content if b.type == "tool_use"), None)
        bloco_texto = next((b.text for b in resposta.content if b.type == "text"), None)
        turno_assistant = {"role": "assistant", "content": [b.model_dump() for b in resposta.content]}
        mensagens.append(turno_assistant)
        novos_turnos.append(turno_assistant)

        if bloco_tool is None:
            return bloco_texto, None, novos_turnos

        if bloco_tool.name == "registrar_pedido_projeto":
            # pedidos_projeto.registrar() ja dispara Planejador+Coder em
            # sequencia -- pode demorar, avisa antes de travar a resposta.
            telegram_transport.enviar(
                chat_id, "Anotado! Deixa eu preparar um rascunho tecnico disso..."
            )
            registro = pedidos_projeto.registrar(
                bloco_tool.input.get("pedido", ""), bloco_tool.input.get("contexto", "")
            )
            if registro["status"] == "rascunho_pronto":
                return None, {"tipo": "pedido", "id": registro["id"]}, novos_turnos
            resultado = {
                "status": _STATUS_PEDIDO_HUMANO.get(registro["status"], registro["status"]),
                "erro": registro.get("erro"),
            }
        else:  # listar_pedidos_projeto
            resultado = {
                "pedidos": [
                    {
                        "pedido": p["pedido"],
                        "status": _STATUS_PEDIDO_HUMANO.get(p["status"], p["status"]),
                        "criado_em": p["criado_em"],
                    }
                    for p in pedidos_projeto.listar()
                ]
            }

        turno_resultado = {
            "role": "user",
            "content": [{
                "type": "tool_result",
                "tool_use_id": bloco_tool.id,
                "content": json.dumps(resultado, ensure_ascii=False),
            }],
        }
        mensagens.append(turno_resultado)
        novos_turnos.append(turno_resultado)

    return "Desculpa, não consegui concluir isso agora — tenta reformular?", None, novos_turnos


def _caminho_estado(chat_id: str):
    pasta = config.DATA_DIR / "conversas_elis"
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta / f"{chat_id}.json"


def _estado_vazio() -> dict:
    return {"historico": [], "pedido_pendente_aplicar": None}


def _carregar_estado(chat_id: str) -> dict:
    caminho = _caminho_estado(chat_id)
    if not caminho.exists():
        return _estado_vazio()
    return json.loads(caminho.read_text(encoding="utf-8"))


def _salvar_estado(chat_id: str, estado: dict) -> None:
    _caminho_estado(chat_id).write_text(
        json.dumps(estado, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def processar_mensagem(chat_id: str, texto: str, telegram_transport) -> None:
    if texto.strip().lower() in ("/start", "/reiniciar"):
        _salvar_estado(chat_id, _estado_vazio())
        telegram_transport.enviar(
            chat_id,
            "Oi! Sou a Elis. Cuido do desenvolvimento do HubMktDigital -- "
            "posso explicar o que ja existe, o que falta, e anotar (e ja "
            "aplicar, com sua confirmacao) pedidos de mudanca no projeto.",
        )
        return

    if texto.strip().lower() == "/status":
        telegram_transport.enviar(chat_id, config.texto_status())
        return

    estado = _carregar_estado(chat_id)

    if estado.get("pedido_pendente_aplicar") is not None:
        pedido_id = estado["pedido_pendente_aplicar"]
        resposta = texto.strip().lower()
        if resposta in ("sim", "s", "yes", "confirmo"):
            telegram_transport.enviar(
                chat_id,
                "Aplicando agora — o bot vai reiniciar sozinho em instantes. "
                "Se algo der errado, ele desfaz e volta sozinho tambem.",
            )
            pedidos_projeto.aplicar(pedido_id)
        else:
            telegram_transport.enviar(
                chat_id,
                "Ok, nao apliquei — o rascunho continua pronto, pode pedir "
                "pra aplicar mais tarde.",
            )
        estado["pedido_pendente_aplicar"] = None
        # O historico salvo termina num tool_use (registrar_pedido_projeto)
        # sem tool_result correspondente -- a API da Anthropic exige o par
        # na mensagem seguinte, entao zera aqui (nas duas respostas).
        estado["historico"] = []
        _salvar_estado(chat_id, estado)
        return

    estado["historico"].append({"role": "user", "content": texto})
    bloco_texto, pendencia, novos_turnos = _perguntar(estado["historico"], chat_id, telegram_transport)
    estado["historico"].extend(novos_turnos)

    if pendencia is not None:
        estado["pedido_pendente_aplicar"] = pendencia["id"]
        telegram_transport.enviar(
            chat_id,
            "Preparei um rascunho tecnico pro seu pedido. Aplicar agora? (sim/nao)",
        )
    elif bloco_texto:
        telegram_transport.enviar(chat_id, bloco_texto)

    _salvar_estado(chat_id, estado)
