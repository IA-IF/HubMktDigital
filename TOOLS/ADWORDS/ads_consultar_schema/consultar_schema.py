"""Consulta ao vivo o schema real (via introspecção protobuf) de
qualquer tipo de mensagem da API do Google Ads instalada -- generaliza
a coleta estática feita em TOOLS/ADWORDS/DOCS/raw/mutate_mensagens.json
para uma tool que o agente pode chamar sob demanda, para QUALQUER tipo
de recurso, não só os que alguém catalogou de antemão.

Cacheado no Redis por tipo de recurso -- o schema de uma classe
protobuf não muda entre chamadas (só mudaria com upgrade de versão da
lib `google-ads` instalada), então recomputar a introspecção inteira
(~900 módulos) a cada chamada é desperdício puro. Cache sem TTL: se a
lib for atualizada, o cache fica desatualizado até alguém limpar --
aceitável pro escopo de hoje, revisar se virar problema real.
"""
import importlib
import json
import pkgutil
import sys
from pathlib import Path

import google.ads.googleads.v24 as v24_pkg

REPO_ROOT = Path(__file__).resolve().parents[3]
PREFIXO_CACHE = "ads_schema:"

LABEL_NOMES = {1: "OPTIONAL", 2: "REQUIRED", 3: "REPEATED"}
TIPO_NOMES = {
    1: "DOUBLE", 2: "FLOAT", 3: "INT64", 4: "UINT64", 5: "INT32",
    6: "FIXED64", 7: "FIXED32", 8: "BOOL", 9: "STRING", 10: "GROUP",
    11: "MESSAGE", 12: "BYTES", 13: "UINT32", 14: "ENUM", 15: "SFIXED32",
    16: "SFIXED64", 17: "SINT32", 18: "SINT64",
}

_INDICE_CLASSES: dict[str, type] = {}


def _indexar_classes() -> None:
    if _INDICE_CLASSES:
        return
    for _, nome_modulo, _ in pkgutil.walk_packages(v24_pkg.__path__, prefix="google.ads.googleads.v24."):
        if ".types" not in nome_modulo:
            continue
        try:
            mod = importlib.import_module(nome_modulo)
        except Exception:
            continue
        for atributo in dir(mod):
            if atributo.startswith("_"):
                continue
            obj = getattr(mod, atributo)
            if atributo in _INDICE_CLASSES:
                continue
            if hasattr(obj, "pb") and callable(getattr(obj, "pb", None)):
                try:
                    if hasattr(obj.pb(), "DESCRIPTOR"):
                        _INDICE_CLASSES[atributo] = obj
                except Exception:
                    continue


def _cliente_redis_ou_none():
    try:
        import redis
        from dotenv import dotenv_values
        env = dotenv_values(REPO_ROOT / "REDIS" / ".env")
        if not env.get("REDIS_URL"):
            return None
        cliente = redis.Redis.from_url(env["REDIS_URL"], decode_responses=True)
        cliente.ping()
        return cliente
    except Exception:
        return None


def _consultar_schema_sem_cache(tipo_recurso: str) -> dict:
    _indexar_classes()
    classe = _INDICE_CLASSES.get(tipo_recurso)
    if classe is None:
        return {"erro": f"tipo de recurso desconhecido: {tipo_recurso}"}
    descriptor = classe.pb().DESCRIPTOR
    campos = []
    for f in descriptor.fields:
        campo = {
            "name": f.name, "number": f.number,
            "type": TIPO_NOMES.get(f.type, f.type),
            "label": LABEL_NOMES.get(f.label, f.label),
        }
        if f.type == 11 and f.message_type is not None:
            campo["message_type"] = f.message_type.name
        if f.type == 14 and f.enum_type is not None:
            campo["enum_type"] = f.enum_type.name
            campo["enum_values"] = [v.name for v in f.enum_type.values]
        if f.containing_oneof is not None:
            campo["oneof"] = f.containing_oneof.name
        campos.append(campo)
    return {"name": descriptor.full_name, "fields": campos}


def consultar_schema(tipo_recurso: str) -> dict:
    cliente_redis = _cliente_redis_ou_none()
    chave = f"{PREFIXO_CACHE}{tipo_recurso}"

    if cliente_redis is not None:
        cacheado = cliente_redis.get(chave)
        if cacheado is not None:
            return json.loads(cacheado)

    resultado = _consultar_schema_sem_cache(tipo_recurso)

    if cliente_redis is not None and "erro" not in resultado:
        cliente_redis.set(chave, json.dumps(resultado, ensure_ascii=False))

    return resultado


if __name__ == "__main__":
    tipo_recurso_arg = sys.argv[2] if len(sys.argv) > 2 else sys.argv[1]
    print(json.dumps(consultar_schema(tipo_recurso_arg), ensure_ascii=False, indent=2))
