"""O Julio: conversa com o humano no Telegram sobre MARKETING de um site
e aciona os outros agentes (GA4/Ads/Search Console/catalogo). Irmao da
Elis (ver elis_orchestrator.py), que cuida do desenvolvimento do proprio
projeto -- so um dos dois fica ativo por vez, escolhido por
AGENTE_ATIVO em REDIS/.env (ver julio_config.agente_ativo(),
main_telegram.py).

O client Anthropic e instanciado direto (nao via LLMRouter.ask*): o
router adiciona cache semantico, mas so ajuda em chamadas cujo prompt
se repete — aqui o historico da conversa muda a cada mensagem, entao
cachear nunca acertaria (mesmo racional documentado em
../llm_router/router.py sobre ask_with_history nunca ser cacheada). Um
tool-loop tambem precisa do objeto de resposta completo (content blocks,
tool_use), que os metodos simplificados do router nao expõem.

Fluxo:
  0. Toda conversa nova comeca sem site definido — o Julio manda um menu
     numerado fechado (1/2/3, Etapa 1 do inteligencia.md) e SO aceita
     resposta por numero, nunca apelido em texto livre (elimina ambiguidade
     de match parcial entre os 3 sites, ver `_site_por_opcao`). Ele NUNCA
     assume um site por padrao: um unico bot atende aos 3, e confundir a
     conta errada tem custo real. Pra trocar de site no meio da conversa,
     mande "/site".
  1. Com o site definido, cada mensagem passa primeiro por
     `discover_tool.descobrir` (Etapa 2 do inteligencia.md: busca vetorial
     no catalogo de TOOLS/**/tool.json no Redis) pra trazer so as tools
     candidatas aquela mensagem — nunca o catalogo inteiro. Mensagem sem
     candidato relevante (ex: "oi") vira `tools=[]`, resposta em texto puro.
     Se a busca vetorial falhar (Redis fora do ar), `_tools_candidatas`
     cai pro catalogo fixo lido direto de TOOLS/**/tool.json (sempre
     atualizado, nunca precisa editar este arquivo quando uma tool nova
     entra). Cada tool.json diz TUDO que o orquestrador precisa pra rodar
     ela (`script`, `modo_entrada`) e se precisa pausar pra confirmacao
     humana antes (`requer_confirmacao`) — ver `agentes.rodar_tool` e
     `_executar_tool_leitura`. Regra inegociavel do prompt: nunca
     inventar resposta nem fingir ter feito algo (por isso existe a tool
     `registrar_pedido_futuro`).
  2. Resposta "sim" a uma proposta pendente de uma tool com
     `requer_confirmacao` (hoje so `criar_campanha`) -> roda a tool de
     verdade NO SITE ESCOLHIDO. Qualquer outra coisa cancela a proposta.

Estado da conversa (site + historico + proposta pendente) e persistido em
data/telegram_conversas/<chat_id>.json para sobreviver a reinicios.
"""
import json

import anthropic

import agentes
import discover_tool
import julio_config as config
import pedidos

MAX_TURNOS_FERRAMENTA = 4

# Schemas/descricoes das tools de LEITURA/ACAO (analise_vendas,
# catalogo_produtos, criar_campanha, registrar_pedido_futuro, etc) NAO
# ficam mais aqui -- moram no tool.json de cada uma, em TOOLS/. Ver
# discover_tool.catalogar_tools()/descobrir() e agentes.rodar_tool().

SCHEMA_PERSONALIDADE = {
    "type": "object",
    "properties": {
        "texto": {
            "type": "string",
            "description": (
                "Texto final e completo da secao 'Personalidade / "
                "comportamento' do GLOBAL.md, pronto pra salvar (markdown, "
                "itens de lista com '-')."
            ),
        },
    },
    "required": ["texto"],
}

DESCRICAO_PERSONALIDADE = (
    "Chame SO quando o humano ja confirmou exatamente como quer a nova "
    "secao de personalidade -- com o texto final completo, pronto pra "
    "salvar. Antes disso, converse, explique o que existe hoje e proponha "
    "mudancas em texto livre; nunca chame so por ele ter descrito uma "
    "ideia, sem voce ter mostrado como ficaria e ele ter concordado."
)

def _sistema(site: str) -> str:
    nome = config.SITE_NOMES.get(site, site)
    return (
        f"Voce e o Julio, agente de marketing. Esta conversa e sobre a "
        f"'{nome}' — nao confunda com os outros sites/clientes que voce "
        "tambem atende. Conversando pelo Telegram com o responsavel de "
        "marketing. Regra geral: prefira AGIR a PERGUNTAR — se uma "
        "ferramenta disponivel nesta chamada (ver `tools`) tem um jeito "
        "razoavel de rodar com o que voce ja sabe (usando os defaults "
        "dela), chame antes de fazer perguntas de qualificacao. Ferramenta "
        "que precisa de confirmacao humana antes de agir de verdade (ver "
        "descricao dela) so deve ser chamada com informacao completa — "
        "pergunte ao usuario so o que realmente faltar, sem re-confirmar "
        "o que ele ja disse. Se o pedido nao se encaixa em NENHUMA "
        "ferramenta disponivel, use `registrar_pedido_futuro` — REGRA "
        "INEGOCIAVEL: nunca invente uma resposta ou finja ter feito algo "
        "que voce nao tem capacidade de fazer.\n\n"
        "IMPORTANTE sobre o RULES.md do site (briefing abaixo): coisas "
        "como 'pausar keyword com gasto > R$50' sao acoes de um pipeline "
        "automatico separado, agendado, nao executadas por voce, Julio. "
        "Use o briefing so como CONTEXTO (publico, orcamento, ROAS-alvo) "
        "pra preencher uma proposta de campanha com bom senso. Se o "
        "usuario pedir uma acao que o briefing menciona mas que nao e "
        "nenhuma das suas ferramentas disponiveis (pausar keyword, ajustar "
        "lance, mudar orcamento de campanha existente, etc.) — voce NAO "
        "PODE fazer isso. Nao diga 'posso fazer' nem confirme a acao: use "
        "`registrar_pedido_futuro` e explique que ainda nao tem essa "
        "capacidade."
    )


def _site_por_opcao(texto: str) -> str | None:
    """Etapa 1 do inteligencia.md: selecao SEMPRE por menu numerado fechado
    (1/2/3), nunca por apelido em texto livre -- elimina ambiguidade de
    match parcial entre os 3 sites."""
    try:
        indice = int(texto.strip()) - 1
    except ValueError:
        return None
    if indice < 0 or indice >= len(config.ORDEM_MENU_SITE):
        return None
    return config.ORDEM_MENU_SITE[indice]


def _perguntar_qual_site(chat_id: str, motivo: str, telegram_transport) -> None:
    linhas = [f"{i + 1} {slug}" for i, slug in enumerate(config.ORDEM_MENU_SITE)]
    telegram_transport.enviar(
        chat_id,
        f"{motivo}selecione o site\n" + "\n".join(linhas),
    )


def _executar_tool_leitura(tool: dict, entrada: dict, site: str) -> dict:
    if tool["name"] == "registrar_pedido_futuro":
        return pedidos.registrar(site, entrada.get("pedido", ""), entrada.get("contexto", ""))
    try:
        return agentes.rodar_tool(tool, site, entrada)
    except Exception as exc:  # noqa: BLE001 — devolve o erro pro LLM decidir o que dizer
        return {"erro": str(exc)}


def _tool_por_nome(nome: str) -> dict | None:
    """Le TOOLS/**/tool.json direto do disco (sem depender do Redis) e
    acha a tool pelo nome -- usado quando precisamos do registro
    completo (script/modo_entrada) fora do fluxo de discover_tool, ex:
    na confirmacao de uma proposta pendente."""
    for tool in discover_tool.catalogar_tools():
        if tool["name"] == nome:
            return tool
    return None


def _tools_candidatas(mensagem: str) -> list[dict]:
    """Devolve os registros COMPLETOS (name/description/input_schema/
    script/modo_entrada/...) das tools candidatas a essa mensagem —
    busca vetorial no Redis (Etapa 2 do inteligencia.md); se o Redis
    estiver fora do ar, cai pro catalogo fixo lido direto de
    TOOLS/**/tool.json (nunca precisa editar este arquivo pra isso)."""
    try:
        return discover_tool.descobrir(mensagem)
    except Exception:  # noqa: BLE001 — Redis fora do ar: cai pro catalogo fixo
        return discover_tool.catalogar_tools()


def _perguntar(historico: list[dict], site: str) -> tuple[str | None, dict | None, list[dict]]:
    client = anthropic.Anthropic(api_key=config.anthropic_api_key())
    global_regras = config.global_md().read_text(encoding="utf-8")
    regras_site = config.regras_negocio(site).read_text(encoding="utf-8")
    sistema = (
        f"{_sistema(site)}\n\n"
        f"=== GLOBAL.md (personalidade, vale pra qualquer site) ===\n{global_regras}\n\n"
        f"=== RULES.md do site atual ===\n{regras_site}"
    )
    ultima_mensagem_usuario = historico[-1]["content"]
    candidatos = _tools_candidatas(ultima_mensagem_usuario)
    catalogo_por_nome = {c["name"]: c for c in candidatos}
    tools = [
        {"name": c["name"], "description": c["description"], "input_schema": c["input_schema"]}
        for c in candidatos
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

        tool_meta = catalogo_por_nome.get(bloco_tool.name) or _tool_por_nome(bloco_tool.name)
        if tool_meta and tool_meta.get("requer_confirmacao"):
            return None, bloco_tool.input, novos_turnos

        if tool_meta is None:
            resultado = {"erro": f"ferramenta desconhecida: {bloco_tool.name}"}
        else:
            resultado = _executar_tool_leitura(tool_meta, bloco_tool.input, site)
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


_MARCADOR_PERSONALIDADE = "## Personalidade / comportamento\n\n"


def _ler_secao_personalidade() -> str:
    conteudo = config.global_md().read_text(encoding="utf-8")
    if _MARCADOR_PERSONALIDADE in conteudo:
        return conteudo.split(_MARCADOR_PERSONALIDADE, 1)[1].strip()
    return conteudo.strip()


def _salvar_secao_personalidade(texto_novo: str) -> None:
    caminho = config.global_md()
    conteudo = caminho.read_text(encoding="utf-8")
    if _MARCADOR_PERSONALIDADE in conteudo:
        prefixo = conteudo.split(_MARCADOR_PERSONALIDADE, 1)[0] + _MARCADOR_PERSONALIDADE
    else:
        prefixo = conteudo.rstrip() + "\n\n" + _MARCADOR_PERSONALIDADE
    caminho.write_text(prefixo + texto_novo.strip() + "\n", encoding="utf-8")


def _conversar_personalidade(historico: list[dict]) -> tuple[str | None, dict | None, list[dict]]:
    client = anthropic.Anthropic(api_key=config.anthropic_api_key())
    atual = _ler_secao_personalidade()
    sistema = (
        "Voce e o Julio, ajudando o proprio operador a reajustar a SUA "
        "PROPRIA personalidade, guardada em AGENTES/julio/GLOBAL.md. "
        "Conteudo atual da secao 'Personalidade / comportamento':\n\n"
        f"{atual}\n\n"
        "Converse normalmente, explique o que ja existe se perguntarem, "
        "proponha como ficaria a mudanca em texto livre. So chame a "
        "ferramenta `salvar_personalidade` quando o humano JA CONFIRMOU "
        "exatamente o texto final."
    )
    tools = [{
        "name": "salvar_personalidade",
        "description": DESCRICAO_PERSONALIDADE,
        "input_schema": SCHEMA_PERSONALIDADE,
    }]

    mensagens = list(historico)
    resposta = client.messages.create(
        model=config.claude_model(), max_tokens=1500,
        system=sistema, tools=tools, messages=mensagens,
    )
    bloco_tool = next((b for b in resposta.content if b.type == "tool_use"), None)
    bloco_texto = next((b.text for b in resposta.content if b.type == "text"), None)
    turno_assistant = {"role": "assistant", "content": [b.model_dump() for b in resposta.content]}
    novos_turnos = [turno_assistant]

    if bloco_tool is not None and bloco_tool.name == "salvar_personalidade":
        return None, bloco_tool.input, novos_turnos
    return bloco_texto, None, novos_turnos


def _ler_personalidade_default() -> str:
    return config.global_md_default().read_text(encoding="utf-8").strip()


def _texto_fix_help() -> str:
    return (
        "Comandos fixos disponiveis:\n\n"
        "/fix_help — mostra esta lista.\n"
        "/fix_redis — reindexa o catalogo de tools no Redis (discover_tool), "
        "incluindo qualquer TOOLS/**/tool.json novo ou alterado desde a "
        "ultima reindexacao.\n"
        "/fix_julio — conversa com voce pra reajustar a personalidade do "
        "Julio (GLOBAL.md), mostra como fica e so salva depois que voce "
        "confirmar.\n"
        "/fix_julio_default — mostra a personalidade original (salva em "
        "GLOBAL.default.md) e restaura ela, desfazendo qualquer ajuste "
        "feito via /fix_julio (pede confirmacao antes de restaurar)."
    )


def _resumo_proposta(site: str, p: dict) -> str:
    nome_site = config.SITE_NOMES.get(site, site)
    kws = ", ".join(f"{k['texto']} [{k.get('tipo_correspondencia', 'BROAD')}]" for k in p["palavras_chave"])
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
    return {
        "site": None, "historico": [], "proposta_pendente": None,
        "ajustando_personalidade": False, "personalidade_pendente": None,
        "historico_personalidade": [],
    }


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
            "qualquer coisa. (Manda /fix_help pra ver os comandos fixos.)",
        )
        _perguntar_qual_site(chat_id, "", telegram_transport)
        return

    if texto.strip().lower() in ("/site", "/trocar-site"):
        estado["site"] = None
        estado["historico"] = []
        estado["proposta_pendente"] = None
        estado["ajustando_personalidade"] = False
        estado["personalidade_pendente"] = None
        estado["historico_personalidade"] = []
        _salvar_estado(chat_id, estado)
        _perguntar_qual_site(chat_id, "", telegram_transport)
        return

    if texto.strip().lower() == "/fix_help":
        telegram_transport.enviar(chat_id, _texto_fix_help())
        return

    if texto.strip().lower() == "/fix_redis":
        telegram_transport.enviar(chat_id, "Reindexando o catalogo de tools no Redis...")
        try:
            total = discover_tool.reindexar()
            telegram_transport.enviar(
                chat_id, f"Pronto — {total} tools reindexadas a partir de TOOLS/**/tool.json."
            )
        except Exception as exc:  # noqa: BLE001 — informar o erro ao usuario
            telegram_transport.enviar(chat_id, f"Erro ao reindexar: {exc}")
        return

    if texto.strip().lower() == "/fix_julio":
        estado["ajustando_personalidade"] = True
        estado["personalidade_pendente"] = None
        estado["historico_personalidade"] = []
        _salvar_estado(chat_id, estado)
        telegram_transport.enviar(
            chat_id,
            "Personalidade atual do Julio:\n\n" + _ler_secao_personalidade() +
            "\n\nO que voce quer mudar? (ou manda \"cancelar\" pra sair sem mudar nada)",
        )
        return

    if texto.strip().lower() == "/fix_julio_default":
        default_texto = _ler_personalidade_default()
        estado["ajustando_personalidade"] = True
        estado["personalidade_pendente"] = default_texto
        estado["historico_personalidade"] = []
        _salvar_estado(chat_id, estado)
        telegram_transport.enviar(
            chat_id,
            "Personalidade padrao (original):\n\n" + default_texto +
            "\n\nRestaurar pra essa, desfazendo qualquer ajuste feito depois? (sim/nao)",
        )
        return

    if estado.get("ajustando_personalidade"):
        resposta = texto.strip().lower()

        if resposta in ("cancelar", "cancela"):
            estado["ajustando_personalidade"] = False
            estado["personalidade_pendente"] = None
            estado["historico_personalidade"] = []
            _salvar_estado(chat_id, estado)
            telegram_transport.enviar(chat_id, "Ok, cancelado — a personalidade nao mudou.")
            return

        if estado.get("personalidade_pendente") is not None:
            if resposta in ("sim", "s", "yes", "confirmo"):
                _salvar_secao_personalidade(estado["personalidade_pendente"])
                telegram_transport.enviar(
                    chat_id, "Salvo — GLOBAL.md atualizado. A proxima conversa ja usa a personalidade nova."
                )
            else:
                telegram_transport.enviar(chat_id, "Ok, nao salvei. Pode continuar explicando o que quer diferente.")
            estado["ajustando_personalidade"] = False
            estado["personalidade_pendente"] = None
            estado["historico_personalidade"] = []
            _salvar_estado(chat_id, estado)
            return

        estado["historico_personalidade"].append({"role": "user", "content": texto})
        bloco_texto, tool_input, novos_turnos = _conversar_personalidade(estado["historico_personalidade"])
        estado["historico_personalidade"].extend(novos_turnos)
        if tool_input is not None:
            estado["personalidade_pendente"] = tool_input["texto"]
            telegram_transport.enviar(
                chat_id,
                "Ficaria assim:\n\n" + tool_input["texto"] + "\n\nConfirma? (sim/nao)",
            )
        elif bloco_texto:
            telegram_transport.enviar(chat_id, bloco_texto)
        _salvar_estado(chat_id, estado)
        return

    if estado["proposta_pendente"] is not None:
        resposta = texto.strip().lower()
        if resposta in ("sim", "s", "yes", "confirmo"):
            proposta = estado["proposta_pendente"]
            telegram_transport.enviar(chat_id, "Criando campanha no Google Ads (PAUSADA)...")
            try:
                tool = _tool_por_nome("criar_campanha")
                resultado = agentes.criar_campanha_ads(tool, proposta, estado["site"])
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
        site = _site_por_opcao(texto)
        if site is None:
            _perguntar_qual_site(chat_id, "Opcao invalida. ", telegram_transport)
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
