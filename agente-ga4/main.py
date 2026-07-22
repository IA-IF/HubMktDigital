"""Agente de auditoria/leitura GA4 — sempre leitura, nunca altera a propriedade.

Uso:
    python main.py --auditar              # saude da propriedade (conversoes, funil)
    python main.py --trafego --dias 7      # resumo de trafego por canal (chamado pelo ../agente-julio)
"""
import argparse
import json
import sys

from src import ga4_auditor, trafego


def main() -> None:
    parser = argparse.ArgumentParser(description="Auditoria/leitura de propriedade GA4")
    grupo = parser.add_mutually_exclusive_group()
    grupo.add_argument("--auditar", action="store_true", help="Roda a auditoria e imprime o resultado")
    grupo.add_argument("--trafego", action="store_true", help="Resumo de trafego + ecommerce por canal")
    parser.add_argument("--dias", type=int, default=7, help="Periodo em dias pra --trafego (default 7)")
    args = parser.parse_args()

    if args.trafego:
        resultado = trafego.resumo_trafego(dias=args.dias)
        print(json.dumps(resultado, ensure_ascii=False))
        return

    if not args.auditar:
        parser.print_help()
        return

    resultado = ga4_auditor.auditar()
    print(json.dumps(resultado, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    sys.exit(main())
