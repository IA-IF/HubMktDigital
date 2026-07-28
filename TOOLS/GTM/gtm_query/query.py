"""Executa QUALQUER método da API do GTM de forma genérica --
resource_path (dotted, ex: 'accounts.containers.workspaces.tags'),
método e parâmetros escolhidos pelo agente, informado por
gtm_consultar_schema. Caminho aninhado é encadeado dinamicamente
(service.accounts().containers().workspaces().tags()...).

Uso:
    echo '{"resource_path": "accounts.containers.workspaces.tags", "metodo": "list", "parametros": {"parent": "..."}}' | python query.py <site>
"""
import json
import sys
from pathlib import Path

from dotenv import dotenv_values
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

REPO_ROOT = Path(__file__).resolve().parents[3]
SCOPES = ["https://www.googleapis.com/auth/tagmanager.readonly"]


def _navegar_recurso(service, resource_path: str):
    obj = service
    for parte in resource_path.split("."):
        metodo_recurso = getattr(obj, parte, None)
        if metodo_recurso is None:
            raise ValueError(f"recurso desconhecido no caminho: {parte} (em {resource_path})")
        obj = metodo_recurso()
    return obj


def executar_query(site: str, resource_path: str, metodo: str, parametros: dict) -> dict:
    comum = dotenv_values(REPO_ROOT / ".env")
    creds = Credentials(
        token=None, scopes=SCOPES,
        client_id=comum["GTM_CLIENT_ID"], client_secret=comum["GTM_CLIENT_SECRET"],
        refresh_token=comum["GTM_REFRESH_TOKEN"], token_uri="https://oauth2.googleapis.com/token",
    )
    service = build("tagmanager", "v2", credentials=creds, cache_discovery=False)

    try:
        recurso_obj = _navegar_recurso(service, resource_path)
    except ValueError as exc:
        return {"ok": False, "erros": [str(exc)]}

    metodo_fn = getattr(recurso_obj, metodo, None)
    if metodo_fn is None:
        return {"ok": False, "erros": [f"metodo desconhecido: {resource_path}.{metodo}"]}

    try:
        resultado = metodo_fn(**parametros).execute()
    except Exception as exc:  # noqa: BLE001 -- erro real da API, formato variavel
        return {"ok": False, "erros": [str(exc)]}

    return {"ok": True, "resultado": resultado}


if __name__ == "__main__":
    site_arg = sys.argv[1] if len(sys.argv) > 1 else "3gfoods"
    entrada = json.load(sys.stdin)
    print(json.dumps(
        executar_query(site_arg, entrada["resource_path"], entrada["metodo"], entrada.get("parametros", {})),
        ensure_ascii=False, indent=2,
    ))
