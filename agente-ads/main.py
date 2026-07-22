"""Agente CMO — orquestra coleta -> análise -> execução -> relatório.

Uso:
    python main.py --dry-run     # modo observador (Fase 5, semanas 1-2)
    python main.py --executar    # aplica mudanças aprovadas pelos guardrails
    python main.py --testar-conexao   # só lista campanhas ativas (Prompt 1)
    python main.py --criar-campanha   # cria campanha a partir de um JSON no stdin
                                       # (chamado pelo ../agente-julio, nao interativo)

A parte conversacional (Telegram, LLM perguntando o que falta pra montar a
campanha) vive em ../agente-julio — este modulo so expõe a capacidade de
"executar", sem saber quem está do outro lado pedindo.
"""
import argparse
import json
import sys

from src import collector, analyst, executor, reporter, config, campaign_builder


def testar_conexao() -> None:
    from google.ads.googleads.client import GoogleAdsClient

    client = GoogleAdsClient.load_from_dict(config.google_ads_config())
    service = client.get_service("GoogleAdsService")
    query = ("SELECT campaign.id, campaign.name FROM campaign "
             "WHERE campaign.status = 'ENABLED'")
    print("Campanhas ativas:")
    encontrou = False
    for row in service.search(customer_id=config.customer_id(), query=query):
        encontrou = True
        print(f"  [{row.campaign.id}] {row.campaign.name}")
    if not encontrou:
        print("  (nenhuma campanha ativa encontrada — conexao OK)")


def rodar(dry_run: bool) -> None:
    print("1/4 Coletando metricas do Google Ads...")
    dados, caminho = collector.coletar_e_salvar()
    print(f"    Coleta salva em {caminho}")

    print("2/4 Analisando com o Claude...")
    analise = analyst.analisar(dados)
    print(f"    {len(analise.get('acoes', []))} acoes recomendadas")

    print(f"3/4 Executando ({'dry-run' if dry_run else 'REAL'})...")
    resultado = executor.executar(analise, dry_run=dry_run)
    print(f"    {len(resultado['executadas'])} executadas, "
          f"{len(resultado['pendentes_aprovacao'])} pendentes de aprovacao, "
          f"{len(resultado['erros'])} erros")

    print("4/4 Gerando relatorio...")
    texto = reporter.gerar_relatorio(dados, analise, resultado, dry_run)
    canais = reporter.enviar(texto)
    print(f"    Relatorio gravado em logs/; enviado via: {canais or 'nenhum canal externo'}")
    print("\n" + texto)


def criar_campanha_via_stdin() -> None:
    """Le uma proposta de campanha (JSON) do stdin e cria no Google Ads.

    Fronteira de processo para quem orquestra a conversa com o humano
    (../agente-julio) pedir a execucao sem precisar importar codigo deste
    modulo. Sempre imprime um unico JSON no stdout — sucesso ou erro — para
    quem chamou processar de forma previsivel.
    """
    proposta = json.load(sys.stdin)
    try:
        resultado = campaign_builder.criar_campanha(proposta)
        print(json.dumps({"ok": True, **resultado}, ensure_ascii=False))
    except Exception as exc:  # noqa: BLE001 — reportar ao chamador, nao derrubar
        print(json.dumps({"ok": False, "erro": str(exc)}, ensure_ascii=False))
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Agente CMO para Google Ads")
    grupo = parser.add_mutually_exclusive_group()
    grupo.add_argument("--dry-run", action="store_true",
                       help="Analisa e recomenda sem executar nada (padrao)")
    grupo.add_argument("--executar", action="store_true",
                       help="Executa as acoes aprovadas pelos guardrails")
    grupo.add_argument("--testar-conexao", action="store_true",
                       help="Testa credenciais listando campanhas ativas")
    grupo.add_argument("--criar-campanha", action="store_true",
                       help="Le uma proposta de campanha (JSON) do stdin e cria no Google Ads")
    args = parser.parse_args()

    if args.testar_conexao:
        testar_conexao()
        return

    if args.criar_campanha:
        criar_campanha_via_stdin()
        return

    # Seguranca: sem flag explicita, roda em dry-run
    rodar(dry_run=not args.executar)


if __name__ == "__main__":
    sys.exit(main())
