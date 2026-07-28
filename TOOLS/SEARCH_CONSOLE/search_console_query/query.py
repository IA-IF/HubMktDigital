"""Executa QUALQUER método de leitura da API do Search Console
(searchanalytics.query, sitemaps.list/get, sites.list/get) de forma
genérica -- recurso e método escolhidos pelo agente, informado por
search_console_consultar_schema, em vez de uma tool nova por
capacidade.

Uso:
    echo '{"recurso": "searchanalytics", "metodo": "query", "parametros": {...}}' | python query.py <site>
"""
import json
import sys
from pathlib import Path

from dotenv import dotenv_values
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

REPO_ROOT = Path(__file__).resolve().parents[3]
SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]


def executar_query(site: str, recurso: str, metodo: str, parametros: dict) -> dict:
    comum = dotenv_values(REPO_ROOT / ".env")
    do_site = dotenv_values(REPO_ROOT / "SITES" / site / ".env")
    if "SC_SITE_URL" not in do_site:
        return {"ok": False, "erros": [f"site '{site}' sem SC_SITE_URL configurado"]}

    creds = Credentials(
        token=None, scopes=SCOPES,
        client_id=comum["SC_CLIENT_ID"], client_secret=comum["SC_CLIENT_SECRET"],
        refresh_token=comum["SC_REFRESH_TOKEN"], token_uri="https://oauth2.googleapis.com/token",
    )
    service = build("searchconsole", "v1", credentials=creds, cache_discovery=False)

    recurso_obj = getattr(service, recurso, None)
    if recurso_obj is None:
        return {"ok": False, "erros": [f"recurso desconhecido: {recurso}"]}
    metodo_fn = getattr(recurso_obj(), metodo, None)
    if metodo_fn is None:
        return {"ok": False, "erros": [f"metodo desconhecido: {recurso}.{metodo}"]}

    parametros_finais = dict(parametros)
    parametros_finais.setdefault("siteUrl", do_site["SC_SITE_URL"])

    try:
        resultado = metodo_fn(**parametros_finais).execute()
    except Exception as exc:  # noqa: BLE001 -- erro real da API, formato variavel
        return {"ok": False, "erros": [str(exc)]}

    return {"ok": True, "resultado": resultado}


if __name__ == "__main__":
    site_arg = sys.argv[1] if len(sys.argv) > 1 else "3gfoods"
    entrada = json.load(sys.stdin)
    print(json.dumps(
        executar_query(site_arg, entrada["recurso"], entrada["metodo"], entrada.get("parametros", {})),
        ensure_ascii=False, indent=2,
    ))
