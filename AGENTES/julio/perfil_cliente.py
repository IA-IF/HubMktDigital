"""Perfil de cliente por site, em Redis -- substitui os SITES/<site>/
RULES.md (hoje vazios, so template) por um hash simples, facil de criar/
atualizar pela propria conversa. Ver plano
docs/superpowers/plans/2026-07-27-pesquisa-tecnica-perfil-cliente.md.

Hash simples (nao SearchIndex/vetor) -- e leitura direta por site, nao
busca semantica. Mesma instancia/infra Redis do resto do projeto
(REDIS/.env), so muda o prefixo de chave.
"""
import sys
from pathlib import Path

import redis

HUB_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HUB_ROOT / "REDIS" / "llm_router"))
import config as llm_config  # noqa: E402

PREFIXO = "cliente:"
SUFIXO = ":perfil"

# Campos do perfil: os 4 do antigo template RULES.md + o que a Elis
# pediu explicitamente e nao estava la (quem e o cliente, o que vende,
# pra quem vende -- mais amplo que so "produtos em foco").
CAMPOS = [
    "quem_e_cliente", "o_que_vende", "pra_quem_vende",
    "publico_alvo", "orcamento_diario_tipico", "roas_alvo", "produtos_em_foco",
]

DESCRICAO_CAMPO = {
    "quem_e_cliente": "Quem e o cliente por tras do site (a empresa/marca).",
    "o_que_vende": "O que o site vende (categoria/tipo de produto).",
    "pra_quem_vende": "Pra quem vende (perfil geral do comprador).",
    "publico_alvo": "Publico-alvo especifico pra campanhas (idade, interesse, regiao etc).",
    "orcamento_diario_tipico": "Orcamento diario tipico de Google Ads, em reais.",
    "roas_alvo": "ROAS-alvo (retorno sobre investimento em anuncio).",
    "produtos_em_foco": "Produtos/linhas em foco pra campanhas atuais.",
}


def _client() -> redis.Redis:
    return redis.Redis.from_url(llm_config.redis_url(), decode_responses=True)


def carregar(site: str) -> dict:
    """Devolve o perfil salvo (dict, campos ausentes nao aparecem —
    ver `campos_faltando` pra saber o que falta)."""
    return _client().hgetall(f"{PREFIXO}{site}{SUFIXO}")


def salvar_campo(site: str, campo: str, valor: str) -> None:
    if campo not in CAMPOS:
        raise ValueError(f"campo de perfil desconhecido: {campo!r}")
    _client().hset(f"{PREFIXO}{site}{SUFIXO}", campo, valor)


def campos_faltando(site: str) -> list[str]:
    atual = carregar(site)
    return [c for c in CAMPOS if not atual.get(c)]
