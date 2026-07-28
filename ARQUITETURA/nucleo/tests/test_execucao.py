import threading
import time

from ARQUITETURA.nucleo.execucao import DespachanteConcorrente


def test_despachante_roda_chats_diferentes_em_paralelo():
    """threading.Barrier(2) so libera as 2 tarefas se AMBAS chegarem
    nele -- se o despachante serializasse por engano (mesmo lock pra
    chats diferentes), uma das duas nunca chegaria e o teste travaria
    ate o timeout do Future.result() abaixo. Prova real de paralelismo,
    nao so ausencia de erro."""
    despachante = DespachanteConcorrente(max_workers=4)
    barreira = threading.Barrier(2, timeout=2)

    def tarefa():
        barreira.wait()

    futuro_1 = despachante.despachar("chat1", tarefa)
    futuro_2 = despachante.despachar("chat2", tarefa)
    futuro_1.result(timeout=3)
    futuro_2.result(timeout=3)
    despachante.encerrar()


def test_despachante_serializa_tarefas_do_mesmo_chat():
    despachante = DespachanteConcorrente(max_workers=4)
    ordem: list[str] = []
    lock_ordem = threading.Lock()
    liberar_a = threading.Event()

    def tarefa_a():
        with lock_ordem:
            ordem.append("a_inicio")
        assert liberar_a.wait(timeout=2), "tarefa_b nao deveria destravar tarefa_a"
        with lock_ordem:
            ordem.append("a_fim")

    def tarefa_b():
        with lock_ordem:
            ordem.append("b_inicio")

    futuro_a = despachante.despachar("chat1", tarefa_a)
    time.sleep(0.05)  # garante que tarefa_a ja comecou e esta esperando o evento
    futuro_b = despachante.despachar("chat1", tarefa_b)
    time.sleep(0.05)
    # tarefa_b nao pode ter comecado -- esta esperando o lock do chat1,
    # que so libera quando tarefa_a termina.
    assert ordem == ["a_inicio"]

    liberar_a.set()
    futuro_a.result(timeout=2)
    futuro_b.result(timeout=2)
    assert ordem == ["a_inicio", "a_fim", "b_inicio"]
    despachante.encerrar()


def test_despachante_propaga_excecao_via_future():
    despachante = DespachanteConcorrente(max_workers=2)

    def tarefa_com_erro():
        raise ValueError("erro de teste")

    futuro = despachante.despachar("chat1", tarefa_com_erro)
    try:
        futuro.result(timeout=2)
        assert False, "deveria ter levantado ValueError"
    except ValueError as exc:
        assert str(exc) == "erro de teste"
    despachante.encerrar()
