from search import search_prompt

EXIT_COMMANDS = {"sair", "exit", "quit"}


def main():
    chain = search_prompt()

    if not chain:
        print("Não foi possível iniciar o chat. Verifique os erros de inicialização.")
        return

    print("Perguntas sobre o PDF. A resposta usa só o que foi recuperado do banco.")
    print("Encerre com sair, ou com Ctrl+C.")
    while True:
        try:
            question = input("\nPERGUNTA: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nEncerrado.")
            return

        if question.lower() in EXIT_COMMANDS:
            print("Encerrado.")
            return
        if not question:
            continue

        try:
            answer = chain.invoke(question)
        except Exception as exc:
            print(f"RESPOSTA: Erro ao consultar o modelo: {exc}")
            continue

        print(f"RESPOSTA: {answer}")


if __name__ == "__main__":
    main()
