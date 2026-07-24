---
name: protocolo-teste-tools
description: >
  Reproduz o protocolo de teste mocado (H/R/I/P) pra validar uma ferramenta
  do catálogo TOOLS/ com dado real, sem gastar token Anthropic. Use quando
  o usuário pedir pra "testar"/"simular" uma ferramenta de TOOLS/ (GA4,
  GTM, ADWORDS, SEARCH_CONSOLE), pedir um teste "mocado" ou "meio mocado",
  ou referenciar esse protocolo/entendendno.md. Não use pra rodar os
  módulos antigos em LEGADO/ — esse protocolo é da arquitetura nova, na
  raiz do projeto, e nunca depende de código ou `.env` dentro de `LEGADO/`.
---

# Protocolo de teste mocado (H/R/I/P)

**Uso restrito a desenvolvimento.** Este protocolo (e os scripts
`teste_mock.py` que ele gera) serve só pra validar a arquitetura nova
enquanto ela está sendo desenhada nesta sessão/projeto. Não tem
utilidade em produção — o `discover_tool`/decisão do LLM mocados aqui
são só placeholders pra testar a parte determinística (credenciais,
chamada de API real) sem gastar token; o agente de verdade, quando for
pra produção, precisa da busca vetorial e da decisão do LLM reais, não
desses mocks fixos.

Nasceu de uma sessão de design em `entendendno.md` (arquitetura nova do
agente conversacional, ver também `inteligencia.md`). Serve pra validar
que uma ferramenta do catálogo `TOOLS/<GRUPO>/<ferramenta>/` funciona com
dado real, **sem** chamar a API da Anthropic — só a parte de decisão
(qual ferramenta usar, o que o LLM diria) é simulada; a chamada à API
externa (GA4/GTM/Ads/Search Console) é sempre real.

## Legenda (a mesma de `entendendno.md`)

- `H` — humano (mensagem de exemplo, escrita fixa no script)
- `R` — Redis / discover_tool (MOCADO — print fixo dizendo qual ferramenta
  "ganhou" a busca vetorial, sem RedisVL de verdade ainda)
- `I` — LLM (MOCADO — print fixo dizendo qual ferramenta ele "decidiu"
  chamar e com quais argumentos; zero chamada à API da Anthropic)
- `P` — Python (REAL — chamada de verdade à API da plataforma, com dado
  de produção)

## Como criar um teste novo

Referência viva: `TOOLS/GA4/consultar_trafego/teste_mock.py`.

1. Arquivo fica dentro da própria pasta da ferramenta:
   `TOOLS/<GRUPO>/<ferramenta>/teste_mock.py`.
2. Credenciais **só** da raiz do projeto novo — nunca de `LEGADO/`:
   - `.env` da raiz — client_id/secret/refresh_token compartilhados entre
     sites (mesmo client OAuth reaproveitado).
   - `SITES/<site>/.env` — valores únicos do site (property_id, container
     id, customer id, etc.).
   - Use `dotenv_values(...)` (não `load_dotenv`, pra não poluir
     `os.environ` global quando o script roda vários sites em sequência).
3. Estrutura do `main()`:
   ```python
   print(f"H: <mensagem de exemplo do usuario>\n")

   print("R: discover_tool (MOCADO — sem busca vetorial real ainda)")
   print("   catalogo consultado: TOOLS/<GRUPO>/, ...")
   print("   top-1 encontrado: <GRUPO>/<ferramenta> (score simulado 0.9x)\n")

   print("I: decide (MOCADO — sem chamada real ao Claude, zero token gasto)")
   print(f"   ferramenta escolhida: <ferramenta>(...)\n")

   print("P: executando a chamada REAL na API...")
   resultado = <funcao_que_chama_a_api_de_verdade>(...)
   print(f"   resultado real: {resultado}\n")

   print("I: resposta final (aqui seria formulada pelo Claude de verdade)")
   print(f"   \"<frase usando os numeros reais de resultado>\"")
   ```
4. Site e outros parâmetros vêm de `sys.argv`, com default sensato (ex:
   `dias=7`), pra rodar rápido tipo `python teste_mock.py 3gfoods` ou
   `python teste_mock.py adoro 30`.
5. Rodar e mostrar a saída do terminal — não resumir, o valor do teste é
   ver o trace completo H→R→I→P→I.

## O que este protocolo NÃO faz

- Não substitui um teste de verdade com o LLM real — é só pra validar a
  parte determinística (credenciais, chamada de API, formato do dado)
  antes de gastar token integrando o `discover_tool`/LLM de verdade.
- Não roda nem importa nada de `LEGADO/` — se uma ferramenta só existe lá
  hoje, a leitura/lógica precisa ser reescrita (mesmo que pequena) dentro
  da pasta da ferramenta em `TOOLS/`, nunca chamando o módulo antigo.
