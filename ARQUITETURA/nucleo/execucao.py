"""Despachante de turnos de conversa -- resolve o bug real de hoje: o
bot (AGENTES/julio/main_telegram.py) é um loop único, single-thread,
onde uma tarefa demorada (ex: registrar_pedido_projeto rodando
Planejador+Coder por minutos) trava o atendimento de QUALQUER outra
conversa. Aqui, tarefas de chats DIFERENTES rodam em paralelo (thread
pool); tarefas do MESMO chat_id são sempre serializadas (lock por
chat), pra nunca ter dois turnos da mesma conversa mutando
EstadoConversa ao mesmo tempo.
"""
import threading
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor


class DespachanteConcorrente:
    def __init__(self, max_workers: int = 8) -> None:
        self._pool = ThreadPoolExecutor(max_workers=max_workers)
        self._locks: dict[str, threading.Lock] = {}
        self._locks_guarda = threading.Lock()

    def _lock_do_chat(self, chat_id: str) -> threading.Lock:
        with self._locks_guarda:
            if chat_id not in self._locks:
                self._locks[chat_id] = threading.Lock()
            return self._locks[chat_id]

    def despachar(self, chat_id: str, tarefa: Callable[[], None]) -> Future:
        lock = self._lock_do_chat(chat_id)

        def rodar() -> None:
            with lock:
                tarefa()

        return self._pool.submit(rodar)

    def encerrar(self, esperar: bool = True) -> None:
        self._pool.shutdown(wait=esperar)
