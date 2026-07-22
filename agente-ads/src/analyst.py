"""Envia os dados coletados ao Claude e retorna ações recomendadas (Prompt 3 do guia).

Usa structured outputs (output_config.format com json_schema) para garantir
JSON válido no formato:
    {"resumo": str, "alertas": [str], "acoes": [{acao, tipo_entidade, ...}]}
"""
import json

from src import config

SCHEMA_ACOES = {
    "type": "object",
    "properties": {
        "resumo": {
            "type": "string",
            "description": "Resumo executivo da situacao das campanhas em 2-4 frases.",
        },
        "alertas": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Situacoes que exigem atencao humana mas nao sao acoes executaveis.",
        },
        "acoes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "acao": {
                        "type": "string",
                        "enum": [
                            "pausar_keyword",
                            "ajustar_lance",
                            "ajustar_orcamento",
                            "negativar_termo",
                            "outra",
                        ],
                    },
                    "tipo_entidade": {
                        "type": "string",
                        "enum": ["campanha", "grupo_anuncio", "keyword"],
                    },
                    "id_entidade": {
                        "type": "string",
                        "description": (
                            "Para keyword: 'campanha_id/grupo_id/criterio_id'. "
                            "Para campanha: 'campanha_id'."
                        ),
                    },
                    "nome_entidade": {"type": "string"},
                    "valor_atual": {"type": ["number", "null"]},
                    "valor_novo": {"type": ["number", "null"]},
                    "justificativa": {"type": "string"},
                    "impacto_estimado_diario_brl": {
                        "type": "number",
                        "description": "Impacto estimado em R$/dia (sempre positivo).",
                    },
                },
                "required": [
                    "acao", "tipo_entidade", "id_entidade", "nome_entidade",
                    "valor_atual", "valor_novo", "justificativa",
                    "impacto_estimado_diario_brl",
                ],
                "additionalProperties": False,
            },
        },
    },
    "required": ["resumo", "alertas", "acoes"],
    "additionalProperties": False,
}


def _montar_prompt(dados: dict) -> str:
    regras = config.CLAUDE_MD.read_text(encoding="utf-8")
    return (
        "Voce e o CMO responsavel pelas campanhas de Google Ads descritas abaixo. "
        "Analise as metricas dos ultimos 30 dias e recomende acoes seguindo "
        "ESTRITAMENTE as regras de decisao e os guardrails do briefing. "
        "Nao recomende acoes fora da lista permitida — se algo mais for necessario, "
        "use acao='outra' (ira para aprovacao humana) ou registre em alertas.\n\n"
        f"=== BRIEFING (CLAUDE.md) ===\n{regras}\n\n"
        f"=== DADOS COLETADOS ===\n{json.dumps(dados, ensure_ascii=False)}"
    )


def _analisar_anthropic(prompt: str) -> dict:
    import anthropic

    client = anthropic.Anthropic(api_key=config.anthropic_api_key())
    with client.messages.stream(
        model=config.claude_model(),
        max_tokens=16000,
        thinking={"type": "adaptive"},
        output_config={"format": {"type": "json_schema", "schema": SCHEMA_ACOES}},
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        response = stream.get_final_message()

    if response.stop_reason == "refusal":
        raise RuntimeError("O modelo recusou a analise — verifique os dados enviados.")

    texto = next(b.text for b in response.content if b.type == "text")
    return json.loads(texto)


def _analisar_openai(prompt: str) -> dict:
    import openai

    client = openai.OpenAI(api_key=config.openai_api_key())
    response = client.chat.completions.create(
        model=config.openai_model(),
        messages=[{"role": "user", "content": prompt}],
        response_format={
            "type": "json_schema",
            "json_schema": {"name": "acoes_ads", "schema": SCHEMA_ACOES, "strict": True},
        },
    )

    escolha = response.choices[0]
    if escolha.finish_reason == "content_filter":
        raise RuntimeError("O modelo recusou a analise — verifique os dados enviados.")

    return json.loads(escolha.message.content)


def analisar(dados: dict) -> dict:
    prompt = _montar_prompt(dados)

    provedor = config.llm_provider()
    if provedor == "anthropic":
        analise = _analisar_anthropic(prompt)
    elif provedor == "openai":
        analise = _analisar_openai(prompt)
    else:
        raise SystemExit(
            f"LLM_PROVIDER='{provedor}' invalido — use 'anthropic' ou 'openai' no .env.<site>."
        )

    caminho = config.DATA_DIR / f"analise_{dados['data_coleta']}.json"
    caminho.write_text(json.dumps(analise, ensure_ascii=False, indent=2), encoding="utf-8")
    return analise


if __name__ == "__main__":
    import sys
    dados = json.loads(open(sys.argv[1], encoding="utf-8").read())
    print(json.dumps(analisar(dados), ensure_ascii=False, indent=2))
