"""O Julio: conversa com o humano no Telegram e aciona os outros agentes.

Fluxo (hoje, so criacao de campanha nova):
  0. Toda conversa nova comeca sem site definido — o Julio pergunta qual dos
     3 sites (Integra Foods, 3G Foods, Adoro) e o assunto antes de mais nada.
     Ele NUNCA assume um site por padrao: um unico bot atende aos 3, e
     confundir a conta errada tem custo real (campanha criada no cliente
     errado). Pra trocar de site no meio da conversa, mande "/site".
  1. Com o site definido, o usuario descreve o que quer (produto, publico,
     orcamento...).
  2. O LLM (Anthropic ou OpenAI, ver config.llm_provider()) conversa e, quando
     tiver informacao suficiente, chama a tool `propor_campanha` em vez de
     responder em texto livre. O briefing usado (guardrails, ticket medio,
     margem) e o `CLAUDE.<site>.md` do site escolhido no passo 0.
  3. O bot formata um resumo da proposta e pergunta "confirma? (sim/nao)".
  4. Resposta "sim" -> aciona agentes.criar_campanha_ads NO SITE ESCOLHIDO
     (sempre PAUSADA no Google Ads). Qualquer outra coisa cancela a proposta.

Estado da conversa (site + historico + proposta pendente) e persistido em
data/telegram_conversas/<chat_id>.json para sobreviver a reinicios. O
historico guarda o formato nativo do provider (blocos da Anthropic ou
mensagens da OpenAI) porque cada API espera sua propria estrutura de volta;
se o LLM_PROVIDER mudar no meio de uma conversa, o historico e descartado em
vez de tentar traduzir entre formatos — mais simples e o pior caso e só
o usuario repetir a última frase.
"""
import json
import re

from src import agentes, config, telegram_transport

SCHEMA_PROPOSTA = {
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
}

DESCRICAO_TOOL = (
    "Chame esta ferramenta quando tiver informacao suficiente para propor "
    "uma campanha completa de Google Ads Pesquisa. Nao chame antes de saber "
    "o produto/nicho, orcamento diario, publico-alvo, palavras-chave e a "
    "URL de destino — pergunte ao usuario o que faltar."
)


def _sistema(site: str) -> str:
    nome = config.SITE_NOMES.get(site, site)
    return (
        f"Voce e o Julio, agente de marketing. Esta conversa e sobre a "
        f"'{nome}' — nao confunda com os outros sites/clientes que voce "
        "tambem atende. Conversando pelo Telegram com o responsavel de marketing para criar "
        "uma campanha nova de Google Ads Pesquisa. Faca perguntas objetivas "
        "ate ter tudo que precisa, use o contexto de negocio abaixo para "
        "sugerir valores razoaveis (orcamento, lances, publico), e so chame "
        "a ferramenta propor_campanha quando a proposta estiver completa."
    )


def _detectar_site(texto: str) -> str | None:
    """Casa o texto contra os apelidos conhecidos de cada site (config.SITES).

    Usa borda de palavra pra "if" nao casar dentro de outra palavra qualquer.
    """
    alvo = texto.strip().lower()
    for slug, apelidos in config.SITES.items():
        for apelido in apelidos:
            if re.search(rf"\b{re.escape(apelido)}\b", alvo):
                return slug
    return None


def _perguntar_qual_site(chat_id: str, motivo: str = "") -> None:
    opcoes = "Integra Foods, 3G Foods ou Adoro"
    telegram_transport.enviar(
        chat_id,
        f"{motivo}Qual site vamos tratar nesta conversa — {opcoes}?",
    )


def _perguntar_anthropic(historico: list[dict], site: str) -> tuple[str | None, dict | None, dict]:
    import anthropic

    client = anthropic.Anthropic(api_key=config.anthropic_api_key())
    regras = config.claude_md(site).read_text(encoding="utf-8")
    resposta = client.messages.create(
        model=config.claude_model(),
        max_tokens=2000,
        system=f"{_sistema(site)}\n\n=== BRIEFING (CLAUDE.{site}.md) ===\n{regras}",
        tools=[{
            "name": "propor_campanha",
            "description": DESCRICAO_TOOL,
            "input_schema": SCHEMA_PROPOSTA,
        }],
        messages=historico,
    )
    bloco_tool = next((b for b in resposta.content if b.type == "tool_use"), None)
    bloco_texto = next((b.text for b in resposta.content if b.type == "text"), None)
    conteudo_assistant = [b.model_dump() for b in resposta.content]
    return bloco_texto, (bloco_tool.input if bloco_tool else None), {
        "role": "assistant", "content": conteudo_assistant,
    }


def _perguntar_openai(historico: list[dict], site: str) -> tuple[str | None, dict | None, dict]:
    import openai

    client = openai.OpenAI(api_key=config.openai_api_key())
    regras = config.claude_md(site).read_text(encoding="utf-8")
    sistema = {
        "role": "system",
        "content": f"{_sistema(site)}\n\n=== BRIEFING (CLAUDE.{site}.md) ===\n{regras}",
    }
    resposta = client.chat.completions.create(
        model=config.openai_model(),
        messages=[sistema, *historico],
        tools=[{
            "type": "function",
            "function": {
                "name": "propor_campanha",
                "description": DESCRICAO_TOOL,
                "parameters": SCHEMA_PROPOSTA,
            },
        }],
    )
    msg = resposta.choices[0].message
    tool_call = (msg.tool_calls or [None])[0]
    tool_input = json.loads(tool_call.function.arguments) if tool_call else None
    return msg.content, tool_input, msg.model_dump()


def _perguntar(historico: list[dict], site: str) -> tuple[str | None, dict | None, dict]:
    provedor = config.llm_provider()
    if provedor == "anthropic":
        return _perguntar_anthropic(historico, site)
    if provedor == "openai":
        return _perguntar_openai(historico, site)
    raise SystemExit(f"LLM_PROVIDER='{provedor}' invalido — use 'anthropic' ou 'openai'.")


def _resumo_proposta(site: str, p: dict) -> str:
    nome_site = config.SITE_NOMES.get(site, site)
    kws = ", ".join(f"{k['texto']} [{k['tipo_correspondencia']}]" for k in p["palavras_chave"])
    linhas = [
        f"PROPOSTA DE CAMPANHA — site: {nome_site} — confirma? (responda sim ou nao)",
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


def _caminho_estado(chat_id: str):
    pasta = config.DATA_DIR / "telegram_conversas"
    pasta.mkdir(exist_ok=True)
    return pasta / f"{chat_id}.json"


def _estado_vazio() -> dict:
    return {
        "site": None,
        "historico": [],
        "proposta_pendente": None,
        "provider": config.llm_provider(),
    }


def _carregar_estado(chat_id: str) -> dict:
    caminho = _caminho_estado(chat_id)
    if not caminho.exists():
        return _estado_vazio()
    estado = json.loads(caminho.read_text(encoding="utf-8"))
    if estado.get("provider") != config.llm_provider():
        estado["historico"] = []
    return estado


def _salvar_estado(chat_id: str, estado: dict) -> None:
    estado["provider"] = config.llm_provider()
    _caminho_estado(chat_id).write_text(
        json.dumps(estado, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def processar_mensagem(chat_id: str, texto: str) -> None:
    estado = _carregar_estado(chat_id)

    if texto.strip().lower() in ("/start", "/reiniciar"):
        estado = _estado_vazio()
        _salvar_estado(chat_id, estado)
        telegram_transport.enviar(
            chat_id,
            "Oi! Sou o Julio, seu agente de marketing. Atendo a Integra "
            "Foods, a 3G Foods e a Adoro — pra nao arriscar mexer na conta "
            "errada, preciso saber com qual estamos trabalhando antes de "
            "qualquer coisa.",
        )
        _perguntar_qual_site(chat_id)
        return

    if texto.strip().lower() in ("/site", "/trocar-site"):
        estado["site"] = None
        estado["historico"] = []
        estado["proposta_pendente"] = None
        _salvar_estado(chat_id, estado)
        _perguntar_qual_site(chat_id)
        return

    if estado["proposta_pendente"] is not None:
        resposta = texto.strip().lower()
        if resposta in ("sim", "s", "yes", "confirmo"):
            proposta = estado["proposta_pendente"]
            telegram_transport.enviar(chat_id, "Criando campanha no Google Ads (PAUSADA)...")
            try:
                resultado = agentes.criar_campanha_ads(proposta, estado["site"])
                telegram_transport.enviar(
                    chat_id,
                    "Campanha criada com sucesso!\n"
                    f"{resultado['campanha_resource']}\n"
                    f"Status: {resultado['status']}",
                )
            except Exception as exc:  # noqa: BLE001 — informar o erro ao usuario
                telegram_transport.enviar(chat_id, f"Erro ao criar a campanha: {exc}")
            estado["proposta_pendente"] = None
            estado["historico"] = []
            _salvar_estado(chat_id, estado)
        else:
            estado["proposta_pendente"] = None
            estado["historico"] = []
            telegram_transport.enviar(chat_id, "Proposta cancelada. Pode me contar o que quer mudar.")
            _salvar_estado(chat_id, estado)
        return

    if estado["site"] is None:
        site = _detectar_site(texto)
        if site is None:
            _perguntar_qual_site(chat_id, motivo="Nao reconheci esse site. ")
            return
        estado["site"] = site
        _salvar_estado(chat_id, estado)
        nome_site = config.SITE_NOMES.get(site, site)
        telegram_transport.enviar(
            chat_id,
            f"Show, vamos tratar da {nome_site}. Me conta que campanha de "
            "Google Ads voce quer criar (produto, publico, orcamento diario, "
            "URL de destino) que eu monto a proposta.",
        )
        return

    estado["historico"].append({"role": "user", "content": texto})
    bloco_texto, tool_input, turno_assistant = _perguntar(estado["historico"], estado["site"])
    estado["historico"].append(turno_assistant)

    if tool_input is not None:
        estado["proposta_pendente"] = tool_input
        telegram_transport.enviar(chat_id, _resumo_proposta(estado["site"], tool_input))
    elif bloco_texto:
        telegram_transport.enviar(chat_id, bloco_texto)

    _salvar_estado(chat_id, estado)
