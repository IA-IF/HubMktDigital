"""Roteador de custo de LLM: cache semantico (Redis) + escolha de modelo.

Duas portas de entrada, deliberadamente diferentes:
- ask(): cacheada, para perguntas isoladas onde a mesma pergunta sempre
  tem a mesma resposta certa (ex: FAQ, teste de conectividade).
- ask_with_history(): so roteada, NUNCA cacheada — o resultado depende do
  historico passado em `messages`, que varia a cada chamada; cachear por
  similaridade de prompt devolveria a resposta de outra conversa/usuario.
"""
import anthropic
import redis
from redisvl.extensions.cache.llm import SemanticCache

import config

_COMPLEXITIES = ("simple", "complex")


def _validar_complexity(complexity: str) -> str:
    if complexity not in _COMPLEXITIES:
        raise ValueError(
            f"complexity invalido: {complexity!r} — use 'simple' ou 'complex'"
        )
    return complexity


class LLMRouter:
    def __init__(self):
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

        self._models = {
            "simple": config.simple_model(),
            "complex": config.complex_model(),
        }
        # Uma instancia de cache por tier: garante que uma resposta gerada
        # pelo modelo barato nunca seja devolvida quando alguem pede o
        # modelo caro, e vice-versa.
        # distance_threshold=0.1: mais estrito que os 0.9 usados para
        # memoria de conversa (agente-conversacional) — decisao deliberada
        # do design spec, porque uma pergunta "parecida mas nao identica"
        # pode ter resposta correta diferente, ao contrario de recall de
        # conversa por similaridade. Explicito aqui para nao depender do
        # default implicito do redisvl (que pode mudar em versoes futuras).
        self._caches = {
            "simple": SemanticCache(
                name="llmcache_simple",
                redis_client=self.redis_client,
                distance_threshold=0.1,
            ),
            "complex": SemanticCache(
                name="llmcache_complex",
                redis_client=self.redis_client,
                distance_threshold=0.1,
            ),
        }

    def _model_for(self, complexity: str) -> str:
        return self._models[_validar_complexity(complexity)]

    def ask(
        self, prompt: str, system: str | None = None, complexity: str = "complex"
    ) -> str:
        complexity = _validar_complexity(complexity)
        cache = self._caches[complexity]

        # `system` muda qual e a resposta certa (ex: "Resuma" com
        # system="Responda em ingles" vs system="Responda em portugues" sao
        # perguntas diferentes) — por isso entra na chave de cache junto
        # com o prompt. A chamada ao LLM em si continua recebendo `system`
        # e `prompt` separados, como o SDK da Anthropic espera.
        cache_key_prompt = f"{system}\n\n{prompt}" if system else prompt

        hits = cache.check(prompt=cache_key_prompt)
        if hits:
            return hits[0]["response"]

        kwargs = {
            "model": self._model_for(complexity),
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system
        response = self.llm_client.messages.create(**kwargs)
        texto = response.content[0].text

        cache.store(prompt=cache_key_prompt, response=texto)
        return texto

    def ask_with_history(
        self,
        messages: list[dict],
        system: str | None = None,
        complexity: str = "complex",
    ) -> str:
        kwargs = {
            "model": self._model_for(complexity),
            "max_tokens": 1024,
            "messages": messages,
        }
        if system:
            kwargs["system"] = system
        response = self.llm_client.messages.create(**kwargs)
        return response.content[0].text
