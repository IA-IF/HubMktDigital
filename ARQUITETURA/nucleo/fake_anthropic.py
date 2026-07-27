"""Test double da API da Anthropic (`anthropic.Anthropic().messages.
create()`), scriptável, sem rede, sem token. Serve pra testar a
mecânica de um loop de tool-calls (pareamento tool_use/tool_result,
tool_use paralelo, retry) contra a MESMA validação que pegaria em
produção -- sem depender de uma decisão real do LLM. Nunca usar em
produção; só em teste.
"""


class _Bloco:
    def __init__(self, tipo: str, **campos):
        self.type = tipo
        for chave, valor in campos.items():
            setattr(self, chave, valor)
        self._campos = campos

    def model_dump(self) -> dict:
        return {"type": self.type, **self._campos}


def fake_tool_use(id: str, name: str, input: dict) -> _Bloco:
    return _Bloco("tool_use", id=id, name=name, input=input)


def fake_text(texto: str) -> _Bloco:
    return _Bloco("text", text=texto)


class _Resposta:
    def __init__(self, content: list[_Bloco]):
        self.content = content


def fake_response(*blocos: _Bloco) -> _Resposta:
    return _Resposta(list(blocos))


def _validar_pareamento_tool_use(mensagens: list[dict]) -> None:
    for i, msg in enumerate(mensagens):
        if msg.get("role") != "assistant" or not isinstance(msg.get("content"), list):
            continue
        ids_tool_use = {
            bloco["id"] for bloco in msg["content"] if isinstance(bloco, dict) and bloco.get("type") == "tool_use"
        }
        if not ids_tool_use:
            continue
        proxima = mensagens[i + 1] if i + 1 < len(mensagens) else {"content": []}
        conteudo_proxima = proxima.get("content", [])
        if not isinstance(conteudo_proxima, list):
            conteudo_proxima = []
        ids_com_resultado = {
            bloco["tool_use_id"] for bloco in conteudo_proxima
            if isinstance(bloco, dict) and bloco.get("type") == "tool_result"
        }
        orfaos = ids_tool_use - ids_com_resultado
        assert not orfaos, f"tool_use sem tool_result pareado: {sorted(orfaos)}"


class _Messages:
    def __init__(self, fila: list[_Resposta]):
        self._fila = fila

    def create(self, **kwargs) -> _Resposta:
        _validar_pareamento_tool_use(kwargs.get("messages", []))
        if not self._fila:
            raise IndexError("ClienteAnthropicFake: fila de respostas roteirizadas esgotou")
        return self._fila.pop(0)


class ClienteAnthropicFake:
    def __init__(self, respostas: list[_Resposta]):
        self.messages = _Messages(list(respostas))
