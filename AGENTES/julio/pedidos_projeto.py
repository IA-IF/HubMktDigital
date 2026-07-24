"""Pedidos de mudanca/funcionalidade no PROPRIO projeto, feitos pelo
gestor no modo projeto do Julio (ver orchestrator._processar_modo_projeto).

Diferente de pedidos.py (registrar_pedido_futuro, sobre MARKETING de um
site) -- aqui o pedido e sobre o HubMktDigital em si, e o registro ja
dispara a execucao automatica: Planejador (REDIS/planejador) quebra o
pedido em tarefas, Coder (REDIS/coder) escreve o codigo de cada uma --
tudo numa branch git nova (pedido/<id>), NUNCA em master. O working tree
que o bot realmente usa (import, leitura de GLOBAL.md/RULES.md etc)
sempre volta pro estado de producao no final, mesmo se algo falhar --
ver o `finally` em executar().
"""
import json
import subprocess
import sys
import uuid
from datetime import datetime
from pathlib import Path

import julio_config as config

HUB_ROOT = config.HUB_ROOT
PEDIDOS_DIR = config.DATA_DIR / "pedidos_projeto"

sys.path.insert(0, str(HUB_ROOT / "REDIS" / "planejador"))
sys.path.insert(0, str(HUB_ROOT / "REDIS" / "coder"))
from planner import Planejador  # noqa: E402
from coder import Coder  # noqa: E402


def _caminho(pedido_id: str) -> Path:
    PEDIDOS_DIR.mkdir(parents=True, exist_ok=True)
    return PEDIDOS_DIR / f"{pedido_id}.json"


def _salvar(registro: dict) -> None:
    _caminho(registro["id"]).write_text(
        json.dumps(registro, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=HUB_ROOT, capture_output=True, text=True, encoding="utf-8"
    )


def registrar(pedido: str, contexto: str = "") -> dict:
    """Salva o pedido e ja chama executar() na mesma chamada -- sem fila
    separada, e o proprio fluxo sincrono do handler do Telegram."""
    pedido_id = uuid.uuid4().hex[:8]
    registro = {
        "id": pedido_id,
        "pedido": pedido,
        "contexto": contexto,
        "status": "registrado",
        "criado_em": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "branch": None,
        "tarefas": None,
        "erro": None,
    }
    _salvar(registro)
    return executar(pedido_id)


def executar(pedido_id: str) -> dict:
    """Planejador -> Coder numa branch isolada. Guardrail: se o working
    tree ja estiver sujo (mudanca real em andamento), aborta sem tocar em
    nada -- nunca assume que pode descartar trabalho alheio. O `finally`
    sempre devolve o working tree pra master, limpo, mesmo se qualquer
    passo falhar."""
    registro = json.loads(_caminho(pedido_id).read_text(encoding="utf-8"))
    branch = f"pedido/{pedido_id}"

    sujo = _git("status", "--porcelain", "--untracked-files=no")
    if sujo.stdout.strip():
        registro["status"] = "erro"
        registro["erro"] = (
            "working tree com mudancas nao commitadas -- abortado sem tocar em nada"
        )
        _salvar(registro)
        return registro

    criou_branch = _git("checkout", "-b", branch)
    if criou_branch.returncode != 0:
        registro["status"] = "erro"
        registro["erro"] = f"nao consegui criar a branch: {criou_branch.stderr.strip()}"
        _salvar(registro)
        return registro

    try:
        plano = Planejador().planejar(registro["pedido"])
        tarefas_resultado = [
            {**tarefa, **Coder().implementar(tarefa)} for tarefa in plano["tarefas"]
        ]
        registro["tarefas"] = tarefas_resultado

        escreveu_algo = any(t.get("escrito") for t in tarefas_resultado)
        if not escreveu_algo:
            registro["status"] = "erro"
            registro["erro"] = "nenhuma tarefa foi escrita com sucesso"
        else:
            _git("add", "-A")
            resumo = registro["pedido"][:72]
            commit = _git("commit", "-m", f"Pedido {pedido_id}: {resumo}")
            if commit.returncode != 0:
                registro["status"] = "erro"
                registro["erro"] = f"nao consegui commitar: {commit.stderr.strip()}"
            else:
                registro["status"] = "rascunho_pronto"
                registro["branch"] = branch
    except Exception as exc:  # noqa: BLE001 -- pedido nao pode travar o bot
        registro["status"] = "erro"
        registro["erro"] = str(exc)
    finally:
        # Garante que master volta limpo, aconteca o que aconteceu acima.
        _git("checkout", "--", ".")
        _git("clean", "-fd")
        _git("checkout", "master")

    _salvar(registro)
    return registro


def aplicar(pedido_id: str) -> dict:
    """Faz merge da branch do pedido em master (working tree ja esta em
    master, executar() deixa assim) e dispara reiniciar_bot.py como
    PROCESSO SEPARADO (setsid nohup) -- precisa sobreviver independente
    deste, porque ele mesmo vai matar e resubir o processo do bot. Se o
    bot nao voltar a responder, reiniciar_bot.py desfaz o merge sozinho
    (git reset --hard pro commit anterior) e sobe de novo."""
    registro = json.loads(_caminho(pedido_id).read_text(encoding="utf-8"))
    if registro.get("status") != "rascunho_pronto" or not registro.get("branch"):
        registro["status"] = "erro"
        registro["erro"] = "nao ha rascunho pronto pra aplicar"
        _salvar(registro)
        return registro

    commit_anterior = _git("rev-parse", "master").stdout.strip()
    merge = _git("merge", "--no-ff", registro["branch"], "-m", f"Aplica pedido {pedido_id}")
    if merge.returncode != 0:
        _git("merge", "--abort")
        registro["status"] = "erro_aplicar"
        registro["erro"] = f"conflito ao aplicar, rascunho preservado na branch: {merge.stderr.strip()}"
        _salvar(registro)
        return registro

    registro["status"] = "aplicando"
    registro["commit_anterior"] = commit_anterior
    _salvar(registro)

    script = Path(__file__).resolve().parent / "reiniciar_bot.py"
    subprocess.Popen(
        ["setsid", "nohup", sys.executable, str(script), pedido_id, commit_anterior],
        cwd=HUB_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )
    return registro


def listar() -> list[dict]:
    PEDIDOS_DIR.mkdir(parents=True, exist_ok=True)
    registros = [
        json.loads(p.read_text(encoding="utf-8")) for p in PEDIDOS_DIR.glob("*.json")
    ]
    return sorted(registros, key=lambda r: r["criado_em"])
