"""Gera o resumo diário e envia por Slack webhook e/ou e-mail (Prompt 5 do guia).

Sempre grava o relatório em logs/relatorio_YYYY-MM-DD.txt; envio externo é
opcional (configurado no .env).
"""
import os
import smtplib
from datetime import date
from email.mime.text import MIMEText

import requests

from src import config


def _linha_acao(a: dict) -> str:
    valores = ""
    if a.get("valor_atual") is not None or a.get("valor_novo") is not None:
        valores = f" ({a.get('valor_atual')} -> {a.get('valor_novo')})"
    return (f"  - [{a['acao']}] {a['nome_entidade']}{valores} — {a['justificativa']} "
            f"(impacto ~R$ {a['impacto_estimado_diario_brl']:.2f}/dia)")


def gerar_relatorio(dados: dict, analise: dict, resultado: dict, dry_run: bool) -> str:
    hoje = date.today().isoformat()
    modo = "DRY-RUN (nenhuma mudanca aplicada)" if dry_run else "EXECUCAO REAL"
    linhas = [
        f"AGENTE CMO — Relatorio diario {hoje} [{modo}]",
        "=" * 60,
        "",
        "RESUMO DO ANALISTA:",
        analise.get("resumo", "(sem resumo)"),
        "",
        f"Analisado: {len(dados['campanhas'])} campanhas, "
        f"{len(dados['grupos_anuncio'])} grupos, {len(dados['keywords'])} keywords "
        f"(ultimos 30 dias).",
        "",
        f"ACOES EXECUTADAS ({len(resultado['executadas'])}):",
    ]
    linhas += [_linha_acao(a) for a in resultado["executadas"]] or ["  (nenhuma)"]

    linhas += ["", f"PENDENTES DE APROVACAO ({len(resultado['pendentes_aprovacao'])}):"]
    linhas += [
        _linha_acao(a) + f"\n    Motivo: {a['motivo_aprovacao']}"
        for a in resultado["pendentes_aprovacao"]
    ] or ["  (nenhuma)"]

    if resultado["erros"]:
        linhas += ["", f"ERROS ({len(resultado['erros'])}):"]
        linhas += [f"  - {a['nome_entidade']}: {a['erro']}" for a in resultado["erros"]]

    alertas = analise.get("alertas", [])
    if alertas:
        linhas += ["", "ALERTAS:"]
        linhas += [f"  - {alerta}" for alerta in alertas]

    texto = "\n".join(linhas)
    caminho = config.LOGS_DIR / f"relatorio_{hoje}.txt"
    caminho.write_text(texto, encoding="utf-8")
    return texto


def enviar(texto: str) -> list[str]:
    """Envia pelos canais configurados; retorna a lista de canais usados."""
    canais = []

    webhook = os.getenv("SLACK_WEBHOOK_URL", "").strip()
    if webhook:
        resp = requests.post(webhook, json={"text": f"```{texto}```"}, timeout=30)
        resp.raise_for_status()
        canais.append("slack")

    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if telegram_token and telegram_chat_id:
        url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
        for i in range(0, len(texto), 4000):
            resp = requests.post(
                url,
                json={"chat_id": telegram_chat_id, "text": texto[i:i + 4000]},
                timeout=30,
            )
            resp.raise_for_status()
        canais.append("telegram")

    smtp_host = os.getenv("SMTP_HOST", "").strip()
    destino = os.getenv("REPORT_EMAIL_TO", "").strip()
    if smtp_host and destino:
        msg = MIMEText(texto, "plain", "utf-8")
        msg["Subject"] = f"Agente CMO — Relatorio {date.today().isoformat()}"
        msg["From"] = os.getenv("SMTP_USER", "agente-cmo")
        msg["To"] = destino
        with smtplib.SMTP(smtp_host, int(os.getenv("SMTP_PORT", "587"))) as smtp:
            smtp.starttls()
            usuario = os.getenv("SMTP_USER", "").strip()
            if usuario:
                smtp.login(usuario, os.getenv("SMTP_PASSWORD", ""))
            smtp.send_message(msg)
        canais.append("email")

    return canais
