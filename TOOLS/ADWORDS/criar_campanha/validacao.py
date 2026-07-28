"""Calculo puro: valida a proposta de campanha antes de gastar uma
chamada de mutate no Google Ads, e converte BRL -> micros (unidade que a
API usa pra dinheiro). Nada aqui fala com a rede -- isso fica em
construtor.py.
"""

MINIMO_TITULOS = 3
MINIMO_DESCRICOES = 2
# Limites reais da API do Google Ads (responsive search ad) -- passar
# disso faz a mutate de verdade ser rejeitada (GoogleAdsException) DEPOIS
# de gastar a chamada, com um erro tecnico feio pro usuario ver. Checar
# aqui pega isso ANTES, sem gastar rede.
MAX_CHARS_TITULO = 30
MAX_CHARS_DESCRICAO = 90


def brl_para_micros(valor_brl: float) -> int:
    return round(valor_brl * 1_000_000)


def validar_proposta(proposta: dict) -> list[str]:
    """Retorna a lista de erros encontrados; lista vazia = proposta valida."""
    erros = []

    for campo in ("nome_campanha", "url_final"):
        if not proposta.get(campo):
            erros.append(f"campo obrigatorio ausente: {campo}")

    valor_orcamento = proposta.get("orcamento_diario_brl")
    if not isinstance(valor_orcamento, (int, float)) or valor_orcamento <= 0:
        erros.append("orcamento_diario_brl precisa ser um numero maior que zero")

    url_final = proposta.get("url_final")
    if url_final and not url_final.startswith("http"):
        erros.append("url_final precisa comecar com http:// ou https://")

    palavras_chave = proposta.get("palavras_chave")
    if not isinstance(palavras_chave, list) or not palavras_chave:
        erros.append("palavras_chave precisa ser uma lista com pelo menos 1 item")
    elif not all(isinstance(kw, dict) and kw.get("texto") for kw in palavras_chave):
        erros.append("cada palavra_chave precisa ter o campo 'texto'")

    titulos = proposta.get("titulos")
    if not isinstance(titulos, list) or len(titulos) < MINIMO_TITULOS:
        erros.append(f"titulos precisa ter pelo menos {MINIMO_TITULOS} itens (regra do responsive search ad)")
    elif isinstance(titulos, list):
        for t in titulos:
            if isinstance(t, str) and len(t) > MAX_CHARS_TITULO:
                erros.append(f"titulo excede {MAX_CHARS_TITULO} caracteres ({len(t)}): {t!r}")

    descricoes = proposta.get("descricoes")
    if not isinstance(descricoes, list) or len(descricoes) < MINIMO_DESCRICOES:
        erros.append(f"descricoes precisa ter pelo menos {MINIMO_DESCRICOES} itens (regra do responsive search ad)")
    elif isinstance(descricoes, list):
        for d in descricoes:
            if isinstance(d, str) and len(d) > MAX_CHARS_DESCRICAO:
                erros.append(f"descricao excede {MAX_CHARS_DESCRICAO} caracteres ({len(d)}): {d!r}")

    return erros
