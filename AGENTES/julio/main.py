"""CLI do agente-julio. Rode dentro de REDIS/agente-julio/:
    python main.py
"""
from agent import ConversationalAgent


def main() -> None:
    try:
        agent = ConversationalAgent()
    except Exception as e:
        print(f"Falha ao iniciar o agente: {e}")
        raise SystemExit(1)

    print("Agente pronto. Digite 'sair' pra encerrar.\n")
    while True:
        try:
            prompt = input("Voce: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nAte mais!")
            break

        if not prompt:
            continue
        if prompt.lower() in {"sair", "exit", "quit"}:
            print("Ate mais!")
            break

        resposta = agent.chat(prompt)
        print(f"Claude: {resposta}\n")


if __name__ == "__main__":
    main()
