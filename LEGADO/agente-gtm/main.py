"""Agente de auditoria GTM — sempre leitura, nunca altera o container.

Uso:
    python main.py --auditar            # config do container (API, estatico)
    python main.py --auditar-dinamico    # site de verdade (Playwright, dataLayer + hits reais)
"""
import argparse
import json
import sys

from src import dataLayer_auditor, gtm_auditor


def main() -> None:
    parser = argparse.ArgumentParser(description="Auditoria de saude do container GTM")
    grupo = parser.add_mutually_exclusive_group()
    grupo.add_argument("--auditar", action="store_true",
                        help="Roda a auditoria estatica (config do container via API)")
    grupo.add_argument("--auditar-dinamico", action="store_true",
                        help="Abre o site de verdade (Playwright) e confere dataLayer + hits reais")
    args = parser.parse_args()

    if args.auditar_dinamico:
        resultado = dataLayer_auditor.auditar()
        print(json.dumps(resultado, ensure_ascii=False, indent=2))
        return

    if not args.auditar:
        parser.print_help()
        return

    resultado = gtm_auditor.auditar()
    print(json.dumps(resultado, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    sys.exit(main())
