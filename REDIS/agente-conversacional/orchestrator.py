"""O Julio: conversa com o humano no Telegram e aciona os outros agentes.

Portado de LEGADO/agente-julio/src/orchestrator.py (2026-07-22) pra rodar
sobre a base Redis. Duas mudancas em relacao ao original:
  - So Anthropic (sem branch OpenAI): o llm_router que essa base usa e
    Anthropic-only, entao nao ha motivo pra manter o dual-provider do Julio
    antigo aqui.
  - O client Anthropic e instanciado direto (nao via LLMRouter.ask*): o
    router adiciona cache semantico, mas so ajuda em chamadas cujo prompt
    se repete — aqui o historico da conversa muda a cada mensagem, entao
    cachear nunca acertaria (mesmo racional documentado em
    ../llm_router/router.py sobre ask_with_history nunca ser cacheada). Um
    tool-loop tambem precisa do objeto de resposta completo (content blocks,
    tool_use), que os metodos simplificados do router nao expõem.

Fluxo:
  0. Toda conversa nova comeca sem site definido — o Julio pergunta qual dos
     3 sites (Integra Foods, 3G Foods, Adoro) e o assunto antes de mais nada.
     Ele NUNCA assume um site por padrao: um unico bot atende aos 3, e
     confundir a conta errada tem custo real. Pra trocar de site no meio da
     conversa, mande "/site".
  1. Com o site definido, o LLM tem 3 ferramentas:
     - `consultar_trafego`: SO LEITURA. Executa na hora e o resultado volta
       pro proprio LLM formular a resposta com numeros reais.
     - `propor_campanha`: monta uma campanha nova de Google Ads e PARA pra
       confirmacao humana (sim/nao) antes de acionar o agente-ads de verdade.
     - `registrar_pedido_futuro`: pra quando o pedido nao se encaixa em
       nenhuma das outras duas. Regra inegociavel do prompt: nunca inventar
       resposta nem fingir ter feito algo.
  2. Resposta "sim" a uma proposta pendente -> agentes.criar_campanha_ads NO
     SITE ESCOLHIDO (sempre PAUSADA no Google Ads). Qualquer outra coisa
     cancela a proposta.

Estado da conversa (site + historico + proposta pendente) e persistido em
data/telegram_conversas/<chat_id>.json para sobreviver a reinicios.
"""
import json
import re

import anthropic

import agentes
import julio_config as config
import pedidos

MAX_TURNOS_FERRAMENTA = 4

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

DESCRICAO_PROPOSTA = (
    "Chame esta ferramenta quando tiver informacao suficiente para propor "
    "uma campanha completa de Google Ads Pesquisa. Nao chame antes de saber "
    "o produto/nicho, orcamento diario, publico-alvo, palavras-chave e a "
    "URL de destino — pergunte ao usuario o que faltar."
)

SCHEMA_TRAFEGO = {
    "type": "object",
    "properties": {
        "dias": {
            "type": "integer",
            "description": (
                "Quantos dias pra tras a partir de hoje. OPCIONAL — se o "
                "usuario nao disse um periodo, NAO pergunte, so omita este "
                "campo (o padrao de 7 dias e aplicado automaticamente)."
            ),
        },
    },
    "required": [],
}

DESCRICAO_TRAFEGO = (
    "Consulta dados REAIS de trafego e ecommerce do Google Analytics deste "
    "site: sessoes, engajamento, compras, receita e ticket medio, total e "
    "por canal de aquisicao (Direct, Paid Search, Organic Search, etc.) — "
    "esse conjunto de numeros e sempre o mesmo, nao da pra escolher outras "
    "metricas. Chame esta ferramenta IMEDIATAMENTE sempre que o usuario "
    "perguntar sobre trafego, desempenho do site, vendas, resultado de "
    "campanha ou canais — sem confirmar periodo antes (o padrao e 7 dias, "
    "so pergunte se o usuario ja tiver pedido outro periodo e voce nao "
    "souber qual) e sem pedir acesso a conta, voce ja tem via API. So "
    "depois de ver o resultado, responda com os numeros reais."
)

SCHEMA_PEDIDO_FUTURO = {
    "type": "object",
    "properties": {
        "pedido": {
            "type": "string",
            "description": "O que o usuario pediu, resumido em 1 frase clara e especifica.",
        },
        "contexto": {
            "type": "string",
            "description": "Detalhes adicionais relevantes da conversa, se houver. Opcional.",
        },
    },
    "required": ["pedido"],
}

DESCRICAO_PEDIDO_FUTURO = (
    "Chame esta ferramenta quando o usuario pedir algo que NENHUMA das "
    "outras ferramentas resolve — ou seja, algo que voce ainda nao sabe "
    "fazer de verdade. Regra inegociavel: NUNCA invente uma resposta, "
    "finja ter executado algo, ou estime/alucine numeros que voce nao "
    "consultou de uma ferramenta real. Nesses casos, chame esta ferramenta "
    "pra registrar o pedido (ele sera analisado e implementado depois, "
    "fora desta conversa), avise o usuario que anotou, e siga a conversa "
    "normalmente."
)


def _sistema(site: str) -> str:
    nome = config.SITE_NOMES.get(site, site)
    return (
        f"Voce e o Julio, agente de marketing. Esta conversa e sobre a "
        f"'{nome}' — nao confunda com os outros sites/clientes que voce "
        "tambem atende. Conversando pelo Telegram com o responsavel de "
        "marketing. Regra geral: prefira AGIR a PERGUNTAR — se uma "
        "ferramenta tem um jeito razoavel de rodar com o que voce ja sabe "
        "(usando os defaults dela), chame antes de fazer perguntas de "
        "qualificacao. Voce tem 3 ferramentas: `consultar_trafego` "
        "(leitura, chame direto sempre que a pergunta for sobre "
        "trafego/desempenho, sem confirmar periodo antes — nao peca "
        "acesso, voce ja tem), `propor_campanha` (monta uma campanha nova "
        "de Google Ads Pesquisa e para pra confirmacao humana — essa sim "
        "precisa de informacao completa antes: produto/nicho, orcamento "
        "diario, publico-alvo, palavras-chave e URL de destino; pergunte "
        "ao usuario so o que realmente faltar, sem re-confirmar o que ele "
        "ja disse) e `registrar_pedido_futuro` (quando o pedido nao se "
        "encaixa em nenhuma das outras — REGRA INEGOCIAVEL: nunca invente "
        "uma resposta ou finja ter feito algo que voce nao tem capacidade "
        "de fazer; registre o pedido com essa ferramenta em vez disso).\n\n"
        "IMPORTANTE sobre o briefing abaixo (CLAUDE.md do site): ele "
        "descreve regras de negocio e guardrails de um OUTRO sistema (o "
        "pipeline automatico agente-ads, que roda separado, agendado, "
        "sem voce) — coisas como 'pausar keyword com gasto > R$50' sao "
        "acoes QUE AQUELE SISTEMA faz, nao coisas que voce, Julio, pode "
        "executar. Use o briefing so como CONTEXTO (publico, orcamento, "
        "ROAS-alvo) pra preencher `propor_campanha` com bom senso. Se o "
        "usuario pedir uma acao que o briefing menciona mas que nao e "
        "nenhuma das suas 3 ferramentas (pausar keyword, ajustar lance, "
        "mudar orcamento de campanha existente, etc.) — voce NAO PODE "
        "fazer isso. Nao diga 'posso fazer' nem confirme a acao: use "
        "`registrar_pedido_futuro` e explique que ainda nao tem essa "
        "capacidade."
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


def _perguntar_qual_site(chat_id: str, motivo: str, telegram_transport) -> None:
    opcoes = "Integra Foods, 3G Foods ou Adoro"
    telegram_transport.enviar(
        chat_id,
        f"{motivo}Qual site vamos tratar nesta conversa — {opcoes}?",
    )


def _executar_tool_leitura(nome: str, entrada: dict, site: str) -> dict:
    if nome == "consultar_trafego":
        dias = int(entrada.get("dias") or 7)
        try:
            return agentes.consultar_trafego_ga4(site, dias)
        except Exception as exc:  # noqa: BLE001 — devolve o erro pro LLM decidir o que dizer
            return {"erro": str(exc)}
    if nome == "registrar_pedido_futuro":
        return pedidos.registrar(site, entrada.get("pedido", ""), entrada.get("contexto", ""))
    return {"erro": f"ferramenta desconhecida: {nome}"}


def _perguntar(historico: list[dict], site: str) -> tuple[str | None, dict | None, list[dict]]:
    client = anthropic.Anthropic(api_key=config.anthropic_api_key())
    regras = config.claude_md(site).read_text(encoding="utf-8")
    sistema = f"{_sistema(site)}\n\n=== BRIEFING (CLAUDE.{site}.md) ===\n{regras}"
    tools = [
        {"name": "propor_campanha", "description": DESCRICAO_PROPOSTA, "input_schema": SCHEMA_PROPOSTA},
        {"name": "consultar_trafego", "description": DESCRICAO_TRAFEGO, "input_schema": SCHEMA_TRAFEGO},
        {"name": "registrar_pedido_futuro", "description": DESCRICAO_PEDIDO_FUTURO, "input_schema": SCHEMA_PEDIDO_FUTURO},
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
        if bloco_tool.name == "propor_campanha":
            return None, bloco_tool.input, novos_turnos

        resultado = _executar_tool_leitura(bloco_tool.name, bloco_tool.input, site)
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

    return "Desculpa, não consegui concluir essa consulta agora — tenta reformular?", None, novos_turnos


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
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta / f"{chat_id}.json"


def _estado_vazio() -> dict:
    return {"site": None, "historico": [], "proposta_pendente": None}


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
        _perguntar_qual_site(chat_id, "", telegram_transport)
        return

    if texto.strip().lower() in ("/site", "/trocar-site"):
        estado["site"] = None
        estado["historico"] = []
        estado["proposta_pendente"] = None
        _salvar_estado(chat_id, estado)
        _perguntar_qual_site(chat_id, "", telegram_transport)
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
            _perguntar_qual_site(chat_id, "Nao reconheci esse site. ", telegram_transport)
            return
        estado["site"] = site
        _salvar_estado(chat_id, estado)
        nome_site = config.SITE_NOMES.get(site, site)
        telegram_transport.enviar(
            chat_id,
            f"Show, vamos tratar da {nome_site}. Pode perguntar sobre "
            "trafego/desempenho do site ou pedir pra eu montar uma campanha "
            "nova de Google Ads.",
        )
        return

    estado["historico"].append({"role": "user", "content": texto})
    bloco_texto, tool_input, novos_turnos = _perguntar(estado["historico"], estado["site"])
    estado["historico"].extend(novos_turnos)

    if tool_input is not None:
        estado["proposta_pendente"] = tool_input
        telegram_transport.enviar(chat_id, _resumo_proposta(estado["site"], tool_input))
    elif bloco_texto:
        telegram_transport.enviar(chat_id, bloco_texto)

    _salvar_estado(chat_id, estado)
