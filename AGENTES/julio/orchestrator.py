"""O Julio: um agente so de conversa no Telegram, cobrindo as duas coisas
que antes eram dois agentes separados (Julio/marketing + Elis/projeto,
ver commit da fusao) -- marketing de site (GA4/Ads/Search Console/
catalogo) E evolucao do proprio HubMktDigital (registrar/aplicar pedido
de mudanca no projeto). So um bot, mais inteligente, decide pelo teor da
mensagem qual dominio se aplica -- ver plano
docs/superpowers/plans/2026-07-27-fusao-agente-fluxo-conversa.md.

O client Anthropic e instanciado direto (nao via LLMRouter.ask*): o
router adiciona cache semantico, mas so ajuda em chamadas cujo prompt se
repete -- aqui o historico da conversa muda a cada mensagem, entao
cachear nunca acertaria (mesmo racional documentado em
../llm_router/router.py sobre ask_with_history nunca ser cacheada). Um
tool-loop tambem precisa do objeto de resposta completo (content blocks,
tool_use), que os metodos simplificados do router nao expõem.

Fluxo:
  0. Toda conversa comeca sem site definido, mas isso NAO bloqueia falar
     sobre o projeto (registrar_pedido_projeto/listar_pedidos_projeto
     ficam sempre disponiveis, sem depender de site). So quando o pedido
     e sobre marketing de um site e nenhum foi escolhido, o Julio pede
     em texto livre ("qual site: Integra Foods, 3G Foods ou Adoro?") e
     so fixa o site quando o humano disser isso EXPLICITAMENTE (tool
     `selecionar_site`, nunca inferido por adivinhacao de palavra —
     regra dura do projeto, ver CLAUDE.md "Site sempre explicito").
     Aceita nome/apelido em texto livre, nao so numero — o menu fechado
     de antes era limitante demais (ver elis.md).
  1. Com o site definido, cada mensagem passa por `discover_tool.descobrir`
     (busca vetorial no catalogo de TOOLS/**/tool.json no Redis) pra
     trazer so as tools candidatas aquela mensagem -- nunca o catalogo
     inteiro. Cada tool.json diz tudo que o orquestrador precisa pra
     rodar ela e se precisa pausar pra confirmacao humana antes
     (`requer_confirmacao`) -- ver `agentes.rodar_tool`.
  2. Resposta "sim" a uma pendencia (proposta de campanha OU pedido de
     mudanca no projeto com rascunho pronto) resolve ela; qualquer outra
     coisa cancela.

Estado da conversa persiste no Redis (memoria_redis.py), nao mais em
JSON local por chat -- um historico so, nao mais um por agente.
"""
import json

import anthropic

import agentes
import discover_tool
import julio_config as config
import memoria_redis
import pedidos
import pedidos_projeto
import perfil_cliente

MAX_TURNOS_FERRAMENTA = 6
MODELO_RESUMO = "claude-haiku-4-5-20251001"

SITES_VALIDOS = list(config.SITE_NOMES.keys())

SCHEMA_SELECIONAR_SITE = {
    "type": "object",
    "properties": {
        "site": {"type": "string", "enum": SITES_VALIDOS, "description": "Slug do site."},
    },
    "required": ["site"],
}

DESCRICAO_SELECIONAR_SITE = (
    "Chame SO quando o humano disser EXPLICITAMENTE com qual site ele "
    "quer trabalhar (Integra Foods, 3G Foods ou Adoro) -- nunca adivinhe "
    "por contexto vago. Depois de chamar, repita o pedido original dele "
    "usando as ferramentas daquele site."
)

SCHEMA_PEDIDO_PROJETO = {
    "type": "object",
    "properties": {
        "pedido": {"type": "string", "description": "Resumo objetivo do que foi pedido, 1-2 frases."},
        "contexto": {"type": "string", "description": "Detalhes adicionais relevantes. Opcional."},
    },
    "required": ["pedido"],
}

DESCRICAO_PEDIDO_PROJETO = (
    "Chame quando descreverem algo que querem MUDAR ou ADICIONAR no "
    "PROPRIO HubMktDigital (o projeto/bot em si) -- ex: 'quero que o bot "
    "tambem avise sobre X'. Nao confundir com pedido de marketing de um "
    "site (isso usa outras ferramentas, ou `registrar_pedido_futuro` se "
    "nenhuma servir). Nao chame so pra responder pergunta sobre o que ja "
    "existe -- isso voce ja sabe pelo contexto desta conversa."
)

SCHEMA_LISTAR_PEDIDOS = {"type": "object", "properties": {}, "required": []}

DESCRICAO_LISTAR_PEDIDOS = (
    "Chame quando perguntarem o status de pedidos de mudanca no PROPRIO "
    "projeto ja feitos antes (ex: 'como estao meus pedidos')."
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

SCHEMA_ATUALIZAR_PERFIL = {
    "type": "object",
    "properties": {
        "campo": {"type": "string", "enum": perfil_cliente.CAMPOS},
        "valor": {"type": "string"},
    },
    "required": ["campo", "valor"],
}

DESCRICAO_ATUALIZAR_PERFIL = (
    "Chame quando o humano disser algo que preenche um campo do perfil "
    "do cliente do site atual (quem e o cliente, o que vende, pra quem "
    "vende, publico-alvo, orcamento diario, ROAS-alvo, produtos em "
    "foco). So chame com o que ele disse explicitamente, nunca invente "
    "um valor. Pergunte um campo faltando SO quando uma tarefa real "
    "precisar dele (ex: montar proposta de campanha) -- nunca faça uma "
    "entrevista completa de uma vez."
)

SCHEMA_PESQUISAR_TECNICA = {
    "type": "object",
    "properties": {
        "tema": {"type": "string", "description": "Tema da pesquisa (ex: 'negative keywords pra ecommerce de alimentos')."},
    },
    "required": ["tema"],
}

DESCRICAO_PESQUISAR_TECNICA = (
    "Chame SO quando pedirem explicitamente pra pesquisar/buscar "
    "tecnicas de campanha de alta conversao pra Google Ads na internet "
    "(ex: 'pesquisa tecnicas novas pra aumentar conversao'). Nunca chame "
    "proativamente, so sob demanda."
)


def _sistema(site: str | None) -> str:
    status_projeto = config.status_projeto_md().read_text(encoding="utf-8")
    base = (
        "Voce e o Julio. Cobre DOIS dominios -- decida pelo teor da "
        "mensagem qual se aplica, sem perguntar qual dominio, so pelo "
        "conteudo:\n"
        "(1) MARKETING de um dos 3 sites que voce atende (Integra Foods, "
        "3G Foods, Adoro) -- trafego, campanhas, GA4/Ads/Search Console/"
        "catalogo.\n"
        "(2) O PROPRIO PROJETO HubMktDigital (o bot/agente em si) -- "
        "explicar o que ja existe/falta (contexto abaixo) e registrar "
        "pedidos de mudanca via `registrar_pedido_projeto`.\n\n"
        "Regra geral pro dominio (1): prefira AGIR a PERGUNTAR -- se uma "
        "ferramenta disponivel nesta chamada tem um jeito razoavel de "
        "rodar com o que voce ja sabe, chame antes de fazer perguntas de "
        "qualificacao. Ferramenta que precisa de confirmacao humana antes "
        "de agir de verdade so deve ser chamada com informacao completa. "
        "REGRA INEGOCIAVEL (vale pros dois dominios): nunca invente "
        "resposta nem finja ter feito algo que voce nao tem capacidade de "
        "fazer -- se nao existe ferramenta pra isso, use "
        "`registrar_pedido_futuro` (marketing) ou `registrar_pedido_projeto` "
        "(projeto).\n\n"
        "REGRA DURA sobre site: nunca adivinhe qual site esta em jogo. Se "
        "a mensagem for sobre marketing e nenhum site foi escolhido "
        "ainda nesta conversa, pergunte em texto livre qual dos 3 "
        "(Integra Foods, 3G Foods ou Adoro) antes de qualquer ferramenta "
        "de marketing -- so chame `selecionar_site` quando o humano tiver "
        "dito isso explicitamente.\n\n"
        f"=== Status do projeto (o que ja existe, o que falta) ===\n{status_projeto}"
    )
    if site is None:
        return base
    nome = config.SITE_NOMES.get(site, site)
    perfil = perfil_cliente.carregar(site)
    faltando = perfil_cliente.campos_faltando(site)
    linhas_perfil = [f"- {c}: {perfil[c]}" for c in perfil_cliente.CAMPOS if c in perfil]
    bloco_perfil = "\n".join(linhas_perfil) if linhas_perfil else "(perfil ainda vazio)"
    return (
        f"{base}\n\n"
        f"=== Site desta conversa: '{nome}' (ja selecionado, nao confunda "
        "com outro) ===\n"
        f"Perfil de cliente conhecido (Redis, nao RULES.md -- esse arquivo "
        f"nao existe mais):\n{bloco_perfil}\n"
        f"Campos ainda faltando: {', '.join(faltando) if faltando else 'nenhum'}. "
        "So pergunte um campo faltando quando uma tarefa REAL precisar dele "
        "(ex: montar proposta de campanha precisa de orcamento/ROAS-alvo) -- "
        "nunca faça entrevista completa de uma vez. Quando o humano responder, "
        "chame `atualizar_perfil_cliente`.\n\n"
        "Use o perfil so como CONTEXTO pra preencher uma proposta de "
        "campanha com bom senso -- nao e uma lista de acoes automaticas. "
        "Se o usuario pedir uma acao que nao e nenhuma das suas ferramentas "
        "disponiveis -- voce NAO PODE fazer isso. Nao diga 'posso fazer': "
        "use `registrar_pedido_futuro`."
    )


def _executar_tool_site(tool: dict, entrada: dict, site: str) -> dict:
    if tool["name"] == "registrar_pedido_futuro":
        return pedidos.registrar(site, entrada.get("pedido", ""), entrada.get("contexto", ""))
    try:
        return agentes.rodar_tool(tool, site, entrada)
    except Exception as exc:  # noqa: BLE001 — devolve o erro pro LLM decidir o que dizer
        return {"erro": str(exc)}


def _tool_por_nome(nome: str) -> dict | None:
    for tool in discover_tool.catalogar_tools():
        if tool["name"] == nome:
            return tool
    return None


def _tools_candidatas(mensagem: str) -> list[dict]:
    try:
        return discover_tool.descobrir(mensagem)
    except Exception:  # noqa: BLE001 — Redis fora do ar: cai pro catalogo fixo
        return discover_tool.catalogar_tools()


def _ferramentas_base() -> list[dict]:
    return [
        {"name": "selecionar_site", "description": DESCRICAO_SELECIONAR_SITE, "input_schema": SCHEMA_SELECIONAR_SITE},
        {"name": "registrar_pedido_projeto", "description": DESCRICAO_PEDIDO_PROJETO, "input_schema": SCHEMA_PEDIDO_PROJETO},
        {"name": "listar_pedidos_projeto", "description": DESCRICAO_LISTAR_PEDIDOS, "input_schema": SCHEMA_LISTAR_PEDIDOS},
    ]


def _ferramentas_site() -> list[dict]:
    """So fazem sentido com um site ja selecionado (perfil de cliente e
    pesquisa de tecnica sao por site)."""
    return [
        {"name": "atualizar_perfil_cliente", "description": DESCRICAO_ATUALIZAR_PERFIL, "input_schema": SCHEMA_ATUALIZAR_PERFIL},
        {"name": "pesquisar_tecnica_campanha", "description": DESCRICAO_PESQUISAR_TECNICA, "input_schema": SCHEMA_PESQUISAR_TECNICA},
    ]


def _pesquisar_tecnica(tema: str, site: str) -> dict:
    """Pesquisa na internet (web search nativo da API Anthropic, sem
    Firecrawl -- ver decisao no plano) e registra o resultado como tarefa
    via `pedidos.registrar` (mesmo mecanismo de `registrar_pedido_futuro`),
    nao como spec markdown automatico."""
    client = anthropic.Anthropic(api_key=config.anthropic_api_key())
    resposta = client.messages.create(
        model=config.claude_model(), max_tokens=1500,
        tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 3}],
        messages=[{
            "role": "user",
            "content": (
                f"Pesquise tecnicas reais de alta conversao pra campanhas de "
                f"Google Ads sobre: {tema}. Foque em algo aplicavel a um "
                f"e-commerce ja existente (nao negocio de servico local sem "
                f"site). Resuma em ate 5 recomendacoes objetivas e curtas, "
                f"cada uma dizendo se depende de configuracao no Google Ads/"
                f"GA4 que precisa ser verificada antes (ex: publico, "
                f"segmentacao, evento de conversao)."
            ),
        }],
    )
    texto = "\n".join(b.text for b in resposta.content if b.type == "text")
    registro = pedidos.registrar(site, f"Pesquisa de tecnica de campanha: {tema}", texto)
    return {"resumo": texto, "registrado_em": registro["arquivo"]}


def _normalizar_palavras_chave(entrada: dict) -> dict:
    """A API da Anthropic nao valida o tipo dos itens de um array do
    input_schema -- o LLM as vezes manda `palavras_chave` como lista de
    strings em vez de {"texto": ..., "tipo_correspondencia": ...}. Sem
    isso, `_resumo_proposta` (e a criacao real depois) quebram com
    'string indices must be integers' ao acessar kw['texto']."""
    palavras_chave = entrada.get("palavras_chave")
    if not isinstance(palavras_chave, list):
        return entrada
    normalizado = dict(entrada)
    normalizado["palavras_chave"] = [
        kw if isinstance(kw, dict) else {"texto": str(kw), "tipo_correspondencia": "BROAD"}
        for kw in palavras_chave
    ]
    return normalizado


def _executar_bloco_tool(
    bloco_tool, site_atual: str | None, catalogo_por_nome: dict,
    chat_id: str, telegram_transport,
) -> tuple[dict, dict | None, str | None]:
    """Executa um unico tool_use block. Devolve (resultado, pendencia,
    site_novo). `pendencia` preenchida significa que essa acao precisa de
    confirmacao humana antes de prosseguir."""
    if bloco_tool.name == "selecionar_site":
        site_novo = bloco_tool.input["site"]
        resultado = {"ok": True, "site": site_novo, "aviso": "site definido, prossiga com o pedido original"}
        return resultado, None, site_novo

    if bloco_tool.name == "registrar_pedido_projeto":
        telegram_transport.enviar(chat_id, "Anotado! Deixa eu preparar um rascunho tecnico disso...")
        registro = pedidos_projeto.registrar(
            bloco_tool.input.get("pedido", ""), bloco_tool.input.get("contexto", "")
        )
        if registro["status"] == "rascunho_pronto":
            pendencia = {"tipo": "pedido_projeto", "id": registro["id"]}
            resultado = {"ok": True, "aviso": "rascunho preparado, aguardando confirmacao do humano"}
            return resultado, pendencia, None
        resultado = {
            "status": _STATUS_PEDIDO_HUMANO.get(registro["status"], registro["status"]),
            "erro": registro.get("erro"),
        }
        return resultado, None, None

    if bloco_tool.name == "listar_pedidos_projeto":
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
        return resultado, None, None

    if bloco_tool.name == "atualizar_perfil_cliente":
        perfil_cliente.salvar_campo(site_atual, bloco_tool.input["campo"], bloco_tool.input["valor"])
        return {"ok": True}, None, None

    if bloco_tool.name == "pesquisar_tecnica_campanha":
        telegram_transport.enviar(chat_id, "Pesquisando tecnicas na internet, um instante...")
        resultado = _pesquisar_tecnica(bloco_tool.input["tema"], site_atual)
        return resultado, None, None

    tool_meta = catalogo_por_nome.get(bloco_tool.name) or _tool_por_nome(bloco_tool.name)
    if tool_meta and tool_meta.get("requer_confirmacao"):
        entrada = _normalizar_palavras_chave(bloco_tool.input)
        pendencia = {"tipo": "campanha", "input": entrada}
        resultado = {"ok": True, "aviso": "proposta preparada, aguardando confirmacao do humano"}
        return resultado, pendencia, None
    if tool_meta is None:
        return {"erro": f"ferramenta desconhecida: {bloco_tool.name}"}, None, None
    if site_atual is None:
        return {"erro": "nenhum site selecionado ainda -- pergunte qual antes de chamar essa ferramenta de novo"}, None, None
    return _executar_tool_site(tool_meta, bloco_tool.input, site_atual), None, None


def _perguntar(
    historico: list[dict], site: str | None, chat_id: str, telegram_transport
) -> tuple[str | None, dict | None, str | None, list[dict]]:
    """Devolve (bloco_texto, pendencia, site_novo, novos_turnos).
    `pendencia` e {"tipo": "campanha", "input": ...} ou
    {"tipo": "pedido_projeto", "id": ...}. `site_novo` vem preenchido se
    `selecionar_site` foi chamado nesta rodada (o chamador salva no
    estado)."""
    client = anthropic.Anthropic(api_key=config.anthropic_api_key())
    site_atual = site
    ultima_mensagem_usuario = historico[-1]["content"]

    mensagens = list(historico)
    novos_turnos: list[dict] = []

    for _ in range(MAX_TURNOS_FERRAMENTA):
        candidatos = _tools_candidatas(ultima_mensagem_usuario) if site_atual else []
        catalogo_por_nome = {c["name"]: c for c in candidatos}
        tools = _ferramentas_base() + (_ferramentas_site() if site_atual else []) + [
            {"name": c["name"], "description": c["description"], "input_schema": c["input_schema"]}
            for c in candidatos
        ]

        resposta = client.messages.create(
            model=config.claude_model(), max_tokens=2000,
            system=_sistema(site_atual), tools=tools, messages=mensagens,
        )
        blocos_tool = [b for b in resposta.content if b.type == "tool_use"]
        bloco_texto = next((b.text for b in resposta.content if b.type == "text"), None)
        turno_assistant = {"role": "assistant", "content": [b.model_dump() for b in resposta.content]}
        mensagens.append(turno_assistant)
        novos_turnos.append(turno_assistant)

        if not blocos_tool:
            return bloco_texto, None, site_atual if site_atual != site else None, novos_turnos

        # A API pode devolver VARIOS tool_use num so turno (chamadas
        # paralelas, ex: usuario responde 2 perguntas numa mensagem so).
        # Cada tool_use precisa de um tool_result pareado na proxima
        # mensagem -- senao a API rejeita o historico inteiro (400) na
        # proxima chamada. Por isso processamos TODOS aqui, mesmo quando
        # um deles vira pendencia (nesse caso os restantes so recebem um
        # resultado placeholder, e retornamos a pendencia no final).
        pendencia_encontrada = None
        resultados_tool = []
        for bloco_tool in blocos_tool:
            if pendencia_encontrada is not None:
                resultado = {"info": "aguardando confirmacao do humano sobre a acao anterior"}
            else:
                resultado, pendencia, site_novo = _executar_bloco_tool(
                    bloco_tool, site_atual, catalogo_por_nome, chat_id, telegram_transport
                )
                if site_novo is not None:
                    site_atual = site_novo
                if pendencia is not None:
                    pendencia_encontrada = pendencia
            resultados_tool.append({
                "type": "tool_result",
                "tool_use_id": bloco_tool.id,
                "content": json.dumps(resultado, ensure_ascii=False),
            })

        turno_resultado = {"role": "user", "content": resultados_tool}
        mensagens.append(turno_resultado)
        novos_turnos.append(turno_resultado)

        if pendencia_encontrada is not None:
            return None, pendencia_encontrada, site_atual if site_atual != site else None, novos_turnos

    return "Desculpa, não consegui concluir essa consulta agora — tenta reformular?", None, site_atual if site_atual != site else None, novos_turnos


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
        "/status — versao e ambiente (EC2/local) do bot.\n"
        "/site — trocar de site no meio da conversa.\n"
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


def _estado_vazio() -> dict:
    return {
        "site": None, "historico": [], "pendente": None,
        "ajustando_personalidade": False, "personalidade_pendente": None,
        "historico_personalidade": [],
    }


def _carregar_estado(chat_id: str) -> dict:
    return memoria_redis.carregar_estado(chat_id, _estado_vazio())


def _salvar_estado(chat_id: str, estado: dict) -> None:
    memoria_redis.salvar_estado(chat_id, estado)


def _atualizar_resumo(chat_id: str, texto_usuario: str, texto_resposta: str) -> None:
    """Agente especialista em extrair contexto -- chamada extra, barata
    (Haiku), sincrona, no fim de cada turno real. Mantem um resumo vivo
    de pendencias/contexto da conversa em Redis (ver elis.md: "camada
    usando redis e um agente especialista em extrair o contexto"). Erro
    aqui nunca deve derrubar a resposta principal ao usuario."""
    try:
        client = anthropic.Anthropic(api_key=config.anthropic_api_key())
        resumo_atual = memoria_redis.carregar_resumo(chat_id)
        resposta = client.messages.create(
            model=MODELO_RESUMO, max_tokens=300,
            system=(
                "Mantenha um resumo curto (max 5 linhas) do que esta em "
                "aberto/pendente nesta conversa com um agente de marketing/"
                "projeto. Responda SO o resumo atualizado, sem comentario."
            ),
            messages=[{
                "role": "user",
                "content": (
                    f"Resumo anterior:\n{resumo_atual or '(vazio)'}\n\n"
                    f"Novo turno -- usuario: {texto_usuario}\n"
                    f"Novo turno -- resposta: {texto_resposta or '(acao sem texto)'}\n\n"
                    "Resumo atualizado:"
                ),
            }],
        )
        texto = next((b.text for b in resposta.content if b.type == "text"), "")
        if texto.strip():
            memoria_redis.salvar_resumo(chat_id, texto.strip())
    except Exception:  # noqa: BLE001 — resumo e conveniencia, nunca derruba a resposta
        pass


def processar_mensagem(chat_id: str, texto: str, telegram_transport) -> None:
    estado = _carregar_estado(chat_id)

    if texto.strip().lower() in ("/start", "/reiniciar"):
        _salvar_estado(chat_id, _estado_vazio())
        telegram_transport.enviar(
            chat_id,
            "Oi! Sou o Julio. Cuido do marketing da Integra Foods, 3G "
            "Foods e Adoro, e tambem do desenvolvimento do proprio "
            "HubMktDigital. Pode falar direto o que precisa — se for "
            "sobre marketing de um site, so pergunto qual assim que "
            "precisar. (Manda /fix_help pra ver os comandos fixos.)",
        )
        return

    if texto.strip().lower() in ("/site", "/trocar-site"):
        estado["site"] = None
        estado["historico"] = []
        estado["pendente"] = None
        estado["ajustando_personalidade"] = False
        estado["personalidade_pendente"] = None
        estado["historico_personalidade"] = []
        _salvar_estado(chat_id, estado)
        telegram_transport.enviar(chat_id, "Ok, qual site: Integra Foods, 3G Foods ou Adoro?")
        return

    if texto.strip().lower() == "/status":
        telegram_transport.enviar(chat_id, config.texto_status())
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

    if estado["pendente"] is not None:
        pendente = estado["pendente"]
        resposta = texto.strip().lower()
        confirmou = resposta in ("sim", "s", "yes", "confirmo")

        if pendente["tipo"] == "campanha":
            if confirmou:
                telegram_transport.enviar(chat_id, "Criando campanha no Google Ads (PAUSADA)...")
                try:
                    tool = _tool_por_nome("criar_campanha")
                    resultado = agentes.criar_campanha_ads(tool, pendente["input"], estado["site"])
                    telegram_transport.enviar(
                        chat_id,
                        "Campanha criada com sucesso!\n"
                        f"{resultado['campanha_resource']}\n"
                        f"Status: {resultado['status']}",
                    )
                except Exception as exc:  # noqa: BLE001 — informar o erro ao usuario
                    telegram_transport.enviar(chat_id, f"Erro ao criar a campanha: {exc}")
            else:
                telegram_transport.enviar(chat_id, "Proposta cancelada. Pode me contar o que quer mudar.")
        else:  # pedido_projeto
            if confirmou:
                telegram_transport.enviar(
                    chat_id,
                    "Aplicando agora — o bot vai reiniciar sozinho em instantes. "
                    "Se algo der errado, ele desfaz e volta sozinho tambem.",
                )
                pedidos_projeto.aplicar(pendente["id"])
            else:
                telegram_transport.enviar(
                    chat_id,
                    "Ok, nao apliquei — o rascunho continua pronto, pode pedir pra aplicar mais tarde.",
                )

        estado["pendente"] = None
        # O historico salvo termina num tool_use sem tool_result
        # correspondente -- a API da Anthropic exige o par na mensagem
        # seguinte, entao zera aqui (nas duas respostas).
        estado["historico"] = []
        _salvar_estado(chat_id, estado)
        return

    estado["historico"].append({"role": "user", "content": texto})
    bloco_texto, pendencia, site_novo, novos_turnos = _perguntar(
        estado["historico"], estado["site"], chat_id, telegram_transport
    )
    estado["historico"].extend(novos_turnos)
    if site_novo is not None:
        estado["site"] = site_novo

    if pendencia is not None:
        if pendencia["tipo"] == "campanha":
            telegram_transport.enviar(chat_id, _resumo_proposta(estado["site"], pendencia["input"]))
        else:
            telegram_transport.enviar(
                chat_id, "Preparei um rascunho tecnico pro seu pedido. Aplicar agora? (sim/nao)"
            )
        estado["pendente"] = pendencia
    elif bloco_texto:
        telegram_transport.enviar(chat_id, bloco_texto)

    _salvar_estado(chat_id, estado)
    _atualizar_resumo(chat_id, texto, bloco_texto)
