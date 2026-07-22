"""Agente conversacional: Claude + memoria semantica no Redis.

Corrige 3 problemas do REDIS/generated-reference-conversational-agent.py
(codigo bruto gerado pelo agent-builder oficial da Redis): usa o SDK real
da Anthropic (nao o hack openai.OpenAI(base_url=...) contra a API da
Anthropic, que nao funciona), usa a REDIS_URL real do projeto, e conta
com o vectorizer local (HFTextVectorizer) que ja e o default do
SemanticMessageHistory - sem custo de API por mensagem.
"""
import anthropic
import redis
from redisvl.extensions.message_history import SemanticMessageHistory

import config

SYSTEM_PROMPT = (
    "You are a helpful assistant that will answer questions based on the "
    "conversation history."
)


class ConversationalAgent:
    def __init__(self, session_name: str = "chat"):
        self.model = config.claude_model()

        try:
            self.redis_client = redis.Redis.from_url(
                config.redis_url(), decode_responses=True
            )
            self.redis_client.ping()
            print("Connected to Redis successfully")
        except redis.ConnectionError as e:
            print(f"Failed to connect to Redis: {e}")
            print("Please check your REDIS_URL and ensure Redis is running.")
            raise

        self.llm_client = anthropic.Anthropic(api_key=config.anthropic_api_key())
        try:
            self.llm_client.messages.create(
                model=self.model,
                max_tokens=5,
                messages=[{"role": "user", "content": "Hello"}],
            )
            print("Connected to LLM successfully")
        except anthropic.AuthenticationError:
            print("LLM authentication failed. Please check your API key.")
            raise

        self.session_manager = SemanticMessageHistory(
            name=session_name,
            redis_client=self.redis_client,
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
            response = self.llm_client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                messages=messages,
            )
        except Exception as e:
            print(f"Error getting LLM response: {e}")
            return "Sorry, I'm having trouble understanding your question. Please try again later."

        assistant_response = response.content[0].text

        try:
            self.session_manager.add_messages([
                {"role": "user", "content": user_input},
                {"role": "assistant", "content": assistant_response},
            ])
        except Exception as e:
            print(f"Error storing conversation: {e}")

        return assistant_response
