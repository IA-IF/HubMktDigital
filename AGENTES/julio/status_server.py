"""Endpoint HTTP na EC2 pra iniciar/parar/checar o bot do Telegram sem
precisar de SSH -- pro gestor conseguir restaurar o funcionamento
sozinho quando o bot trava. Ver plano
docs/superpowers/plans/2026-07-27-status-controle-bot-ec2.md.

So biblioteca padrao (http.server) -- projeto nao tem Flask/FastAPI hoje
(ver AGENTES/julio/requirements.txt) e nao vale introduzir dependencia
nova so pra 3 endpoints pequenos.

Roda como PROCESSO SEPARADO do bot (mesma razao do reiniciar_bot.py: se
vivesse dentro do main_telegram.py, morreria junto quando o bot travar,
que e exatamente o cenario que isso precisa cobrir). Uso:

    python status_server.py
"""
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

import bot_processo
import julio_config as config

TOKEN_HEADER = "X-Status-Token"


class Handler(BaseHTTPRequestHandler):
    def _token_valido(self) -> bool:
        return self.headers.get(TOKEN_HEADER) == config.status_token()

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
            "bot_vivo": bot_processo.bot_vivo(),
            "ambiente": config.ambiente(),
        })

    def do_POST(self) -> None:
        if self.path == "/iniciar":
            if not self._autorizar():
                return
            bot_processo.subir_bot()
            self._responder(200, {"ok": True, "acao": "iniciar"})
            return
        if self.path == "/parar":
            if not self._autorizar():
                return
            bot_processo.matar_bot()
            self._responder(200, {"ok": True, "acao": "parar"})
            return
        self._responder(404, {"erro": "rota desconhecida"})

    def log_message(self, format: str, *args) -> None:  # noqa: A002 — assinatura da stdlib
        pass  # silencia o log padrao (viraria stderr do processo separado)


def main() -> None:
    porta = config.status_server_port()
    servidor = HTTPServer(("0.0.0.0", porta), Handler)
    print(f"status_server ouvindo na porta {porta}")
    servidor.serve_forever()


if __name__ == "__main__":
    main()
