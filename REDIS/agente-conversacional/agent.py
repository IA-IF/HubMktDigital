"""Agente conversacional: Claude + memoria semantica no Redis.

Chamadas ao LLM passam pelo llm_router (../llm_router) em vez do SDK
Anthropic direto: __init__ usa router.ask() com o mesmo prompt de sempre
("Hello") — candidata perfeita a cache; chat() usa router.ask_with_history()
porque o historico da conversa varia a cada chamada, entao nunca deve ser
cacheado (ver REDIS/llm_router/router.py).
"""
import sys
from pathlib import Path

from redisvl.extensions.message_history import SemanticMessageHistory

# llm_router e um pacote irmao (REDIS/llm_router), nao um subpacote deste
# modulo — este projeto nao usa setup.py/pyproject, entao adicionamos o
# caminho manualmente antes do import.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "llm_router"))
from router import LLMRouter  # noqa: E402

SYSTEM_PROMPT = (
    "You are a helpful assistant that will answer questions based on the "
    "conversation history."
)


class ConversationalAgent:
    def __init__(self, session_name: str = "chat"):
        self.router = LLMRouter()

        try:
            self.router.ask("Hello")
            print("Connected to LLM successfully")
        except Exception as e:
            print(f"LLM connection error: {e}")
            raise

        self.session_manager = SemanticMessageHistory(
            name=session_name,
            redis_client=self.router.redis_client,
        )
        # Looser than redisvl's own default (0.3): we'd rather pull in
        # some borderline-relevant history than miss a useful match, since
        # this is a small prototype where recall matters more than
        # precision. Set once here instead of on every chat() call.
        self.session_manager.set_distance_threshold(0.9)

    def chat(self, user_input: str) -> str:
        # get_relevant() ranks by semantic distance, not chronological
        # order, so its results could otherwise start with role="assistant"
        # (e.g. if a past assistant reply is the closest match). The
        # Anthropic Messages API requires messages[0].role == "user", so an
        # assistant-first context would make the call below raise and fall
        # through to the generic except below (silent loss of memory, no
        # signal that memory was the cause). role="user" restricts context
        # to past user turns only, guaranteeing this can't happen: context
        # is user-only, and we append a fresh user message next.
        context = self.session_manager.get_relevant(
            user_input, top_k=8, role="user"
        )

        messages = list(context)
        messages.append({"role": "user", "content": user_input})

        try:
            assistant_response = self.router.ask_with_history(
                messages, system=SYSTEM_PROMPT
            )
        except Exception as e:
            print(f"Error getting LLM response: {e}")
            return "Sorry, I'm having trouble understanding your question. Please try again later."

        try:
            self.session_manager.add_messages([
                {"role": "user", "content": user_input},
                {"role": "assistant", "content": assistant_response},
            ])
        except Exception as e:
            print(f"Error storing conversation: {e}")

        return assistant_response
