"""Endpoint HTTP pra iniciar/parar/checar o bot do nucleo v2 sem
precisar de SSH -- substitui AGENTES/julio/status_server.py (que
controlava main_telegram.py). Mesma porta e mesmo STATUS_TOKEN de
REDIS/.env de sempre, entao os arquivos em GESTOR/*.command continuam
funcionando sem nenhuma mudanca, agora falando com o processo novo.

Roda como processo SEPARADO do bot (mesma razao de sempre: se vivesse
dentro de main.py, morreria junto quando o bot travar, que e
exatamente o cenario que isso precisa cobrir). Uso:

    python -m ARQUITETURA.nucleo.status_server
"""
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

from dotenv import dotenv_values

from ARQUITETURA.nucleo import status as bot_status

TOKEN_HEADER = "X-Status-Token"
ENV = dotenv_values(bot_status.ENV_FILE)


class Handler(BaseHTTPRequestHandler):
    def _token_valido(self) -> bool:
        return self.headers.get(TOKEN_HEADER) == ENV.get("STATUS_TOKEN")

    def _responder(self, status: int, corpo: dict) -> None:
        payload = json.dumps(corpo, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _autorizar(self) -> bool:
        if self._token_valido():
            return True
        self._responder(401, {"erro": "token invalido ou ausente"})
        return False

    def do_GET(self) -> None:
        if self.path != "/status":
            self._responder(404, {"erro": "rota desconhecida"})
            return
        if not self._autorizar():
            return
        self._responder(200, {
            "bot_vivo": bot_status.bot_vivo(),
            "ambiente": bot_status.ambiente(),
            "arquitetura": "nucleo_v2",
        })

    def do_POST(self) -> None:
        if self.path == "/iniciar":
            if not self._autorizar():
                return
            bot_status.subir_bot()
            self._responder(200, {"ok": True, "acao": "iniciar"})
            return
        if self.path == "/parar":
            if not self._autorizar():
                return
            bot_status.matar_bot()
            self._responder(200, {"ok": True, "acao": "parar"})
            return
        self._responder(404, {"erro": "rota desconhecida"})

    def log_message(self, format: str, *args) -> None:  # noqa: A002 -- assinatura da stdlib
        pass  # silencia o log padrao (viraria stderr do processo separado)


def main() -> None:
    porta = int(ENV.get("STATUS_SERVER_PORT", "8765"))
    servidor = HTTPServer(("0.0.0.0", porta), Handler)
    print(f"status_server (nucleo v2) ouvindo na porta {porta}")
    servidor.serve_forever()


if __name__ == "__main__":
    main()
