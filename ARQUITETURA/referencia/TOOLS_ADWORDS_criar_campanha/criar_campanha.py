"""Tool de criacao de campanha no Google Ads -- valida a proposta e cria
tudo (orcamento, campanha, targeting, grupo, keywords, anuncio) sempre
PAUSADA. Ativar e decisao manual de quem revisa no Google Ads.

Uso:
    echo '{"nome_campanha": "...", ...}' | python criar_campanha.py <site>
    echo '{...}' | python criar_campanha.py 3gfoods

Credenciais so da raiz do projeto (.env + SITES/<site>/.env).
"""
import json
import sys
from pathlib import Path

from dotenv import dotenv_values
from google.ads.googleads.client import GoogleAdsClient

sys.path.insert(0, str(Path(__file__).resolve().parent))

from construtor import executar_criacao
from validacao import validar_proposta

REPO_ROOT = Path(__file__).resolve().parents[3]  # TOOLS/ADWORDS/criar_campanha -> raiz do projeto


def _client_e_customer_id(site: str) -> tuple[GoogleAdsClient, str]:
    comum = dotenv_values(REPO_ROOT / ".env")
    do_site = dotenv_values(REPO_ROOT / "SITES" / site / ".env")
    if "GOOGLE_ADS_CUSTOMER_ID" not in do_site or not do_site["GOOGLE_ADS_CUSTOMER_ID"]:
        raise SystemExit(
            f"Site '{site}' nao tem GOOGLE_ADS_CUSTOMER_ID configurado — confirme que "
            f"SITES/{site}/.env existe e tem essa variavel."
        )
    cfg = {
        "developer_token": comum["GOOGLE_ADS_DEVELOPER_TOKEN"],
        "client_id": comum["GOOGLE_ADS_CLIENT_ID"],
        "client_secret": comum["GOOGLE_ADS_CLIENT_SECRET"],
        "refresh_token": comum["GOOGLE_ADS_REFRESH_TOKEN"],
        "use_proto_plus": True,
    }
    if comum.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID"):
        cfg["login_customer_id"] = comum["GOOGLE_ADS_LOGIN_CUSTOMER_ID"]
    client = GoogleAdsClient.load_from_dict(cfg)
    cid = do_site["GOOGLE_ADS_CUSTOMER_ID"].replace("-", "")
    return client, cid


def criar_campanha(site: str, proposta: dict) -> dict:
    erros = validar_proposta(proposta)
    if erros:
        return {"ok": False, "erros": erros}

    client, cid = _client_e_customer_id(site)
    resultado = executar_criacao(client, cid, proposta)
    return {"ok": True, **resultado}


if __name__ == "__main__":
    site_arg = sys.argv[1] if len(sys.argv) > 1 else "3gfoods"
    proposta_stdin = json.load(sys.stdin)
    print(json.dumps(criar_campanha(site_arg, proposta_stdin), ensure_ascii=False, indent=2))
