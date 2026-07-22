"""Auditoria de saude do container GTM — sempre leitura, nunca publica nada.

Ve gtm-workflow.md (pasta HubMktDigital) para o desenho completo. Este modulo
cobre a auditoria estatica (le a config do container via API); a auditoria
dinamica (navegar o site de verdade e capturar o dataLayer ao vivo) fica pra
depois, como decisao em aberto no brainstorm.md.
"""
import json
from datetime import date

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from src import config

SCOPES = ["https://www.googleapis.com/auth/tagmanager.readonly"]

# Trigger built-in "All Pages" — nao aparece em workspaces().triggers().list(),
# entao nao deve ser tratado como referencia quebrada.
TRIGGER_BUILTIN_ALL_PAGES = "2147479553"


def _service():
    creds = Credentials(token=None, scopes=SCOPES, **config.gtm_credentials_config())
    return build("tagmanager", "v2", credentials=creds, cache_discovery=False)


def _workspace_ativo(service, container_path: str) -> dict:
    """Usa o primeiro workspace do container (normalmente o unico em uso)."""
    resposta = service.accounts().containers().workspaces().list(
        parent=container_path
    ).execute()
    workspaces = resposta.get("workspace", [])
    if not workspaces:
        raise RuntimeError(f"Nenhum workspace encontrado em {container_path}")
    return workspaces[0]


def _tags_sem_trigger(tags: list[dict]) -> list[str]:
    return [t["name"] for t in tags if not t.get("firingTriggerId")]


def _triggers_orfaos(tags: list[dict], triggers: list[dict]) -> list[str]:
    referenciados = {
        trigger_id
        for tag in tags
        for trigger_id in tag.get("firingTriggerId", [])
    }
    return [t["name"] for t in triggers if t["triggerId"] not in referenciados]


def _tag_ga4_config(tags: list[dict], measurement_id_esperado: str) -> dict:
    """Procura a tag 'Google tag' (type=googtag) e confere o Measurement ID."""
    for tag in tags:
        if tag.get("type") != "googtag":
            continue
        tag_id = next(
            (p.get("value") for p in tag.get("parameter", []) if p.get("key") == "tagId"),
            None,
        )
        return {
            "encontrada": True,
            "nome": tag["name"],
            "measurement_id_configurado": tag_id,
            "bate_com_esperado": tag_id == measurement_id_esperado,
        }
    return {"encontrada": False}


def auditar() -> dict:
    service = _service()
    container_path = config.gtm_container_path()

    container = service.accounts().containers().get(path=container_path).execute()
    workspace = _workspace_ativo(service, container_path)
    workspace_path = workspace["path"]

    tags = service.accounts().containers().workspaces().tags().list(
        parent=workspace_path
    ).execute().get("tag", [])
    triggers = service.accounts().containers().workspaces().triggers().list(
        parent=workspace_path
    ).execute().get("trigger", [])
    variables = service.accounts().containers().workspaces().variables().list(
        parent=workspace_path
    ).execute().get("variable", [])

    try:
        versao_live = service.accounts().containers().versions().live(
            parent=container_path
        ).execute()
        tags_live = len(versao_live.get("tag", []))
    except Exception:  # noqa: BLE001 — container pode nunca ter sido publicado
        versao_live = None
        tags_live = 0

    resultado = {
        "data_auditoria": date.today().isoformat(),
        "container": container.get("name"),
        "container_path": container_path,
        "workspace": workspace.get("name"),
        "publicId": container.get("publicId"),
        "resumo": {
            "tags": len(tags),
            "triggers": len(triggers),
            "variaveis": len(variables),
            "tags_na_versao_live": tags_live,
            "tem_mudancas_nao_publicadas": versao_live is not None and tags_live != len(tags),
            "nunca_publicado": versao_live is None,
        },
        "achados": {
            "tags_sem_trigger": _tags_sem_trigger(tags),
            "triggers_orfaos": _triggers_orfaos(tags, triggers),
            "tag_ga4": _tag_ga4_config(tags, config.ga4_measurement_id()),
        },
    }

    caminho = config.DATA_DIR / f"gtm_auditoria_{resultado['data_auditoria']}.json"
    caminho.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
    return resultado


if __name__ == "__main__":
    resultado = auditar()
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
