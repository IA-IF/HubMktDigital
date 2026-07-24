"""Calculo puro: valida a proposta de campanha antes de gastar uma
chamada de mutate no Google Ads, e converte BRL -> micros (unidade que a
API usa pra dinheiro). Nada aqui fala com a rede -- isso fica em
construtor.py.
"""

MINIMO_TITULOS = 3
MINIMO_DESCRICOES = 2


def brl_para_micros(valor_brl: float) -> int:
    return round(valor_brl * 1_000_000)


def validar_proposta(proposta: dict) -> list[str]:
    """Retorna a lista de erros encontrados; lista vazia = proposta valida."""
    erros = []

    for campo in ("nome_campanha", "url_final"):
        if not proposta.get(campo):
            erros.append(f"campo obrigatorio ausente: {campo}")

    for campo in ("orcamento_diario_brl", "lance_inicial_brl"):
        valor = proposta.get(campo)
        if not isinstance(valor, (int, float)) or valor <= 0:
            erros.append(f"{campo} precisa ser um numero maior que zero")

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

    descricoes = proposta.get("descricoes")
    if not isinstance(descricoes, list) or len(descricoes) < MINIMO_DESCRICOES:
        erros.append(f"descricoes precisa ter pelo menos {MINIMO_DESCRICOES} itens (regra do responsive search ad)")

    return erros
