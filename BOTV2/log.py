from BOTV2.config import LOG_FILE


def registrar(nome: str, texto: str) -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as arquivo:
        arquivo.write(f"{nome}: {texto}\n\n")
