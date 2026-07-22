"""Agente de auditoria GTM — sempre leitura, nunca altera o container.

Uso:
    python main.py --auditar
"""
import argparse
import json
import sys

from src import gtm_auditor


def main() -> None:
    parser = argparse.ArgumentParser(description="Auditoria de saude do container GTM")
    parser.add_argument("--auditar", action="store_true", help="Roda a auditoria e imprime o resultado")
    args = parser.parse_args()

    if not args.auditar:
        parser.print_help()
        return

    resultado = gtm_auditor.auditar()
    print(json.dumps(resultado, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    sys.exit(main())
