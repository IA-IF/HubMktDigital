"""
REFERENCIA CRUA gerada pelo AI agent builder oficial da Redis
(https://redis.io/docs/latest/develop/ai/agent-builder/), opcao
"Conversational Assistant" -> Python -> Anthropic (Claude), em 2026-07-22.

NAO RODAR DIRETO. Isso e so o ponto de partida que o site gerou, pra
adaptar no design real (ver conversa de brainstorming). Problemas
conhecidos que a adaptacao precisa resolver:

1. Usa o SDK da OpenAI (openai.OpenAI) apontando pra
   base_url=https://api.anthropic.com/v1/ — isso NAO e como a API da
   Anthropic funciona de verdade (Messages API tem formato proprio,
   nao e compativel com o client da OpenAI). Precisa trocar pelo SDK
   oficial `anthropic`.
2. Usa `SemanticMessageHistory` (RedisVL) — isso faz busca vetorial por
   similaridade no historico (top_k=8 mensagens relevantes), o que exige
   um MODELO DE EMBEDDING configurado (local via HFTextVectorizer, ou via
   API paga tipo OpenAI embeddings). Isso e uma decisao de custo/arquitetura
   que ainda nao foi tomada — ver conversa.
3. Le REDIS_HOST/PORT/PASSWORD direto do ambiente, sem usar a conexao real
   do projeto (REDIS/CLAUDE.md tem a URL redis://default:...@...:19990).
4. Loop de input() e sincrono/blocking — ok pra CLI de teste, mas repensar
   se plugar em outro canal depois.
"""

from redisvl.extensions.message_history import SemanticMessageHistory
import redis
import os
import openai


class ConversationalAgent:
    def __init__(self, session_name="chat"):
        # Get API key from environment variables
        self.llm_api_key = os.getenv('LLM_API_KEY')
        if not self.llm_api_key:
            raise ValueError("LLM_API_KEY environment variable is required")
        self.llm_base_url = os.getenv('LLM_API_BASE_URL', 'https://api.anthropic.com/v1/')
        self.llm_model = os.getenv('LLM_MODEL', 'claude-3-5-sonnet-latest')

        # Connect to Redis
        try:
            self.redis_client = redis.Redis(
                host=os.getenv('REDIS_HOST', 'localhost'),
                port=int(os.getenv('REDIS_PORT', 6379)),
                username=os.getenv('REDIS_USERNAME', 'default'),
                password=os.getenv('REDIS_PASSWORD', ''),
                decode_responses=True
            )
            self.redis_client.ping()
            print("Connected to Redis successfully")
        except redis.ConnectionError as e:
            print(f"Failed to connect to Redis: {e}")
            print("Please check your Redis connection settings and ensure Redis is running.")
            raise
        except Exception as e:
            print(f"Redis connection error: {e}")
            raise

        # Initialize LLM client with error handling
        try:
            self.client = openai.OpenAI(api_key=self.llm_api_key, base_url=self.llm_base_url)
            test_response = self.client.chat.completions.create(
                model=self.llm_model,
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=5
            )
            print("Connected to LLM successfully")
        except openai.AuthenticationError:
            print("LLM authentication failed. Please check your API key.")
            raise
        except Exception as e:
            print(f"LLM connection error: {e}")
            raise

        # Initialize session manager
        self.session_manager = SemanticMessageHistory(
            name=session_name,
            redis_client=self.redis_client
        )

    def chat(self, user_input: str, session_tag: str = None) -> str:
        self.session_manager.set_distance_threshold(0.9)
        context = self.session_manager.get_relevant(user_input, top_k=8)

        messages = [{"role": "system", "content": "You are a helpful assistant that will answer questions based on the conversation history."}]
        messages.extend(context)
        messages.append({"role": "user", "content": user_input})

        try:
            response = self.client.chat.completions.create(
                model=self.llm_model,
                messages=messages
            )
        except Exception as e:
            print(f"Error getting LLM response: {e}")
            return "Sorry, I'm having trouble understanding your question. Please try again later."

        assistant_response = response.choices[0].message.content

        try:
            self.session_manager.add_messages([
                {"role": "user", "content": user_input},
                {"role": "assistant", "content": assistant_response}
            ], session_tag)
        except Exception as e:
            print(f"Error storing conversation: {e}")

        return assistant_response


if __name__ == "__main__":
    try:
        agent = ConversationalAgent()
        print(agent.chat("Tell me about yourself."))
        while True:
            try:
                prompt = input('Enter a prompt: ')
                if prompt.lower() in ['quit', 'exit', 'bye']:
                    print("Thanks for using! Goodbye!")
                    break
                print(agent.chat(prompt))
            except KeyboardInterrupt:
                print("\n\nGoodbye!")
                break
            except Exception as e:
                print(f"An error occurred: {e}")
                print("Please try again or type 'quit' to exit.")
    except ValueError as e:
        print(f"Configuration error: {e}")
        print("Please check your environment variables and try again.")
        exit(1)
    except Exception as e:
        print(f"Failed to initialize the conversational agent: {e}")
        exit(1)
