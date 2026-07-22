"""Agente de auditoria GA4 — sempre leitura, nunca altera a propriedade.

Uso:
    python main.py --auditar
"""
import argparse
import json
import sys

from src import ga4_auditor


def main() -> None:
    parser = argparse.ArgumentParser(description="Auditoria de saude da propriedade GA4")
    parser.add_argument("--auditar", action="store_true", help="Roda a auditoria e imprime o resultado")
    args = parser.parse_args()

    if not args.auditar:
        parser.print_help()
        return

    resultado = ga4_auditor.auditar()
    print(json.dumps(resultado, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    sys.exit(main())
