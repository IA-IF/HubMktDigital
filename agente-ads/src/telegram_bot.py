"""Bot conversacional do Telegram para CRIAR campanhas novas no Google Ads.

Diferente do fluxo principal (main.py: collector -> analyst -> executor), que
otimiza campanhas ja existentes de forma agendada, este modulo roda como um
processo continuo (long polling) e deixa o responsavel de marketing conversar
com o agente para desenhar uma campanha nova. So chat_ids na whitelist
(TELEGRAM_AUTHORIZED_CHAT_IDS no .env) podem usa-lo.

Fluxo:
  1. Usuario descreve o que quer (produto, publico, orcamento...).
  2. Claude conversa e, quando tiver informacao suficiente, chama a tool
     `propor_campanha` em vez de responder em texto livre.
  3. O bot formata um resumo da proposta e pergunta "confirma? (sim/nao)".
  4. Resposta "sim" -> cria a campanha via campaign_builder.criar_campanha
     (sempre como PAUSADA). Qualquer outra coisa cancela a proposta.

Estado da conversa (historico + proposta pendente) e persistido em
data/telegram_conversas/<chat_id>.json para sobreviver a reinicios do processo.
"""
import json
import time

import anthropic
import requests

from src import campaign_builder, config

API_BASE = "https://api.telegram.org/bot{token}/{metodo}"

TOOL_PROPOR_CAMPANHA = {
    "name": "propor_campanha",
    "description": (
        "Chame esta ferramenta quando tiver informacao suficiente para propor "
        "uma campanha completa de Google Ads Pesquisa. Nao chame antes de saber "
        "o produto/nicho, orcamento diario, publico-alvo, palavras-chave e a "
        "URL de destino — pergunte ao usuario o que faltar."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "nome_campanha": {"type": "string"},
            "orcamento_diario_brl": {"type": "number"},
            "lance_inicial_brl": {
                "type": "number",
                "description": "Lance de CPC inicial do grupo de anuncios.",
            },
            "palavras_chave": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "texto": {"type": "string"},
                        "tipo_correspondencia": {
                            "type": "string",
                            "enum": ["BROAD", "PHRASE", "EXACT"],
                        },
                    },
                    "required": ["texto", "tipo_correspondencia"],
                },
                "minItems": 3,
            },
            "titulos": {
                "type": "array",
                "items": {"type": "string", "maxLength": 30},
                "minItems": 3,
                "maxItems": 15,
                "description": "Titulos do anuncio responsivo de pesquisa (max 30 caracteres cada).",
            },
            "descricoes": {
                "type": "array",
                "items": {"type": "string", "maxLength": 90},
                "minItems": 2,
                "maxItems": 4,
                "description": "Descricoes do anuncio (max 90 caracteres cada).",
            },
            "url_final": {"type": "string"},
        },
        "required": [
            "nome_campanha", "orcamento_diario_brl", "lance_inicial_brl",
            "palavras_chave", "titulos", "descricoes", "url_final",
        ],
    },
}


def _telegram(metodo: str, **params) -> dict:
    token = config.telegram_bot_token()
    resp = requests.post(API_BASE.format(token=token, metodo=metodo), json=params, timeout=35)
    resp.raise_for_status()
    return resp.json()


def _enviar(chat_id: str, texto: str) -> None:
    for i in range(0, len(texto), 4000):
        _telegram("sendMessage", chat_id=chat_id, text=texto[i:i + 4000])


def _caminho_estado(chat_id: str):
    pasta = config.DATA_DIR / "telegram_conversas"
    pasta.mkdir(exist_ok=True)
    return pasta / f"{chat_id}.json"


def _carregar_estado(chat_id: str) -> dict:
    caminho = _caminho_estado(chat_id)
    if caminho.exists():
        return json.loads(caminho.read_text(encoding="utf-8"))
    return {"historico": [], "proposta_pendente": None}


def _salvar_estado(chat_id: str, estado: dict) -> None:
    _caminho_estado(chat_id).write_text(
        json.dumps(estado, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _resumo_proposta(p: dict) -> str:
    kws = ", ".join(f"{k['texto']} [{k['tipo_correspondencia']}]" for k in p["palavras_chave"])
    linhas = [
        "PROPOSTA DE CAMPANHA — confirma? (responda sim ou nao)",
        f"Nome: {p['nome_campanha']}",
        f"Orcamento diario: R$ {p['orcamento_diario_brl']:.2f}",
        f"Lance inicial: R$ {p['lance_inicial_brl']:.2f}",
        f"Palavras-chave: {kws}",
        f"URL final: {p['url_final']}",
        "Titulos: " + " | ".join(p["titulos"]),
        "Descricoes: " + " | ".join(p["descricoes"]),
        "",
        "A campanha sera criada PAUSADA — alguem precisa ativa-la manualmente "
        "no Google Ads apos revisar.",
    ]
    return "\n".join(linhas)


def _perguntar_claude(historico: list[dict]) -> dict:
    regras = config.CLAUDE_MD.read_text(encoding="utf-8")
    client = anthropic.Anthropic(api_key=config.anthropic_api_key())
    sistema = (
        "Voce e o agente de marketing da Integra Foods, conversando pelo "
        "Telegram com o responsavel de marketing para criar uma campanha nova "
        "de Google Ads Pesquisa. Faca perguntas objetivas ate ter tudo que "
        "precisa, use o contexto de negocio abaixo para sugerir valores "
        "razoaveis (orcamento, lances, publico), e so chame a ferramenta "
        "propor_campanha quando a proposta estiver completa.\n\n"
        f"=== BRIEFING (CLAUDE.md) ===\n{regras}"
    )
    resposta = client.messages.create(
        model=config.claude_model(),
        max_tokens=2000,
        system=sistema,
        tools=[TOOL_PROPOR_CAMPANHA],
        messages=historico,
    )
    return resposta


def _processar_mensagem(chat_id: str, texto: str) -> None:
    estado = _carregar_estado(chat_id)

    if estado["proposta_pendente"] is not None:
        resposta = texto.strip().lower()
        if resposta in ("sim", "s", "yes", "confirmo"):
            proposta = estado["proposta_pendente"]
            _enviar(chat_id, "Criando campanha no Google Ads (PAUSADA)...")
            try:
                resultado = campaign_builder.criar_campanha(proposta)
                _enviar(
                    chat_id,
                    "Campanha criada com sucesso!\n"
                    f"{resultado['campanha_resource']}\n"
                    f"Status: {resultado['status']}",
                )
            except Exception as exc:  # noqa: BLE001 — informar o erro ao usuario
                _enviar(chat_id, f"Erro ao criar a campanha: {exc}")
            estado["proposta_pendente"] = None
            estado["historico"] = []
            _salvar_estado(chat_id, estado)
        else:
            estado["proposta_pendente"] = None
            estado["historico"] = []
            _enviar(chat_id, "Proposta cancelada. Pode me contar o que quer mudar.")
            _salvar_estado(chat_id, estado)
        return

    if texto.strip().lower() in ("/start", "/reiniciar"):
        estado = {"historico": [], "proposta_pendente": None}
        _salvar_estado(chat_id, estado)
        _enviar(
            chat_id,
            "Oi! Sou o agente de marketing da Integra Foods. Me conta que "
            "campanha de Google Ads voce quer criar (produto, publico, "
            "orcamento diario, site de destino) que eu monto a proposta.",
        )
        return

    estado["historico"].append({"role": "user", "content": texto})
    resposta = _perguntar_claude(estado["historico"])

    bloco_tool = next((b for b in resposta.content if b.type == "tool_use"), None)
    bloco_texto = next((b.text for b in resposta.content if b.type == "text"), None)

    conteudo_assistant = [b.model_dump() for b in resposta.content]
    estado["historico"].append({"role": "assistant", "content": conteudo_assistant})

    if bloco_tool is not None:
        estado["proposta_pendente"] = bloco_tool.input
        _enviar(chat_id, _resumo_proposta(bloco_tool.input))
    elif bloco_texto:
        _enviar(chat_id, bloco_texto)

    _salvar_estado(chat_id, estado)


def rodar_loop() -> None:
    autorizados = config.telegram_authorized_chat_ids()
    if not autorizados:
        raise SystemExit(
            "TELEGRAM_AUTHORIZED_CHAT_IDS vazio no .env — defina ao menos um "
            "chat_id autorizado antes de rodar o bot."
        )

    print(f"Bot rodando. Chat_ids autorizados: {autorizados}")
    offset = None
    while True:
        try:
            params = {"timeout": 30}
            if offset is not None:
                params["offset"] = offset
            resposta = _telegram("getUpdates", **params)
        except requests.RequestException as exc:
            print(f"Erro de rede, tentando de novo em 5s: {exc}")
            time.sleep(5)
            continue

        for update in resposta.get("result", []):
            offset = update["update_id"] + 1
            mensagem = update.get("message")
            if not mensagem or "text" not in mensagem:
                continue
            chat_id = str(mensagem["chat"]["id"])
            if chat_id not in autorizados:
                _enviar(chat_id, "Voce nao esta autorizado a usar este bot.")
                continue
            try:
                _processar_mensagem(chat_id, mensagem["text"])
            except Exception as exc:  # noqa: BLE001 — nao derrubar o loop por erro de 1 msg
                print(f"Erro processando mensagem de {chat_id}: {exc}")
                try:
                    _enviar(chat_id, f"Erro interno: {exc}")
                except requests.RequestException:
                    pass


if __name__ == "__main__":
    rodar_loop()
