"""Escuta o bot telegram_v2 (t.me/iftelegramv2_bot) dentro do grupo
(Eduardo + Leandro + bot) e loga cada mensagem em BOTV2/logs/conversa.md.
Nao responde nada sozinho -- so grava; quem decide e envia a resposta sou
eu (Claude), via `python -m BOTV2.enviar "texto"`.

Requer privacy mode desativado no @BotFather (/setprivacy -> Disable),
senao o bot so enxerga mensagens que comecem com "/" ou que o mencionem.

Uso:
    python -m BOTV2.escutar
"""
from BOTV2.canal import receber_atualizacoes
from BOTV2.config import NOMES_POR_USUARIO_ID, carregar, salvar_grupo_chat_id
from BOTV2.log import registrar


def rodar() -> None:
    token, autorizados = carregar()
    print(f"telegram_v2 escutando. Usuarios autorizados: {autorizados}")
    offset = None
    while True:
        atualizacoes = receber_atualizacoes(token, offset)
        for atualizacao in atualizacoes:
            offset = atualizacao["update_id"] + 1
            mensagem = atualizacao.get("message")
            remetente = mensagem.get("from") if mensagem else None
            if not mensagem or "text" not in mensagem or not remetente:
                continue
            usuario_id = str(remetente["id"])
            if usuario_id not in autorizados:
                continue
            salvar_grupo_chat_id(str(mensagem["chat"]["id"]))
            nome = NOMES_POR_USUARIO_ID.get(usuario_id, usuario_id)
            texto = mensagem["text"]
            registrar(nome, texto)
            print(f"[{nome}] {texto}")


if __name__ == "__main__":
    rodar()
