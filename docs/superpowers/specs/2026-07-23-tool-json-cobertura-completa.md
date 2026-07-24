# Spec: tool.json pra todo script de TOOLS/ com entrypoint CLI+JSON

## Problema

`discover_tool` (busca vetorial no Redis, usada pelo Julio) so enxerga
tool que tem `tool.json` ao lado. Hoje 3 scripts que ja funcionam e ja
sao usados pelas skills de auditoria NAO tem `tool.json`, entao o Julio
nunca consegue chama-los:

- `TOOLS/ADWORDS/analise_vendas/analise_ads.py`
- `TOOLS/SEARCH_CONSOLE/analise_vendas/analise_organico.py`
- `TOOLS/SEARCH_CONSOLE/analise_vendas/analise_tecnica.py`

Bonus: os 3 moram em pastas chamadas `analise_vendas` (mesmo nome da
pasta de GA4, que faz outra coisa) — por isso o `name` de cada
`tool.json` usa o nome real da funcao (`analise_ads`,
`analise_organico`, `analise_tecnica`), nunca `analise_vendas`, pra nao
colidir no catalogo.

## Regra pra identificar "e uma tool"

Um script em `TOOLS/**/*.py` e uma tool candidata a `tool.json` se:
1. Tem bloco `if __name__ == "__main__":`
2. Esse bloco termina em `print(json.dumps(...))` (contrato:
   stdout = 1 JSON, nada mais — e o que `agentes.py._rodar()` espera)
3. Ainda nao tem `tool.json` no mesmo diretorio

Modulos internos (`coleta.py`, `funil.py`, `validacao.py`, `test_*.py`
etc) NAO contam — so o arquivo com o entrypoint.

## Como preencher cada campo

- `name`: nome da funcao principal do modulo (`rodar_analise_ads` ->
  `analise_ads`), nunca o nome da pasta.
- `plataforma`: a API que o script consulta de verdade (`ADWORDS`,
  `GA4`, `SEARCH_CONSOLE`, `geral`).
- `description`: 1-2 frases dizendo o que devolve de verdade (metricas
  exatas) + "So leitura" quando aplicavel — mesmo padrao dos 4
  `tool.json` que ja existem.
- `input_schema`: espelha o parse de `sys.argv` do bloco `__main__` —
  todo argv com fallback (`sys.argv[N] if len(...) > N else <default>`)
  vira campo OPCIONAL no schema, com o mesmo default documentado na
  `description` do campo. Nenhum campo novo alem do que o script ja
  aceita.

## Depois de criar

Rodar `/fix_redis` (ou `discover_tool.reindexar()` direto) pra essas
tools novas entrarem no indice do Redis — sem isso o Julio continua
sem enxerga-las mesmo com o `tool.json` no lugar certo.

## Observacoes da execucao (2026-07-23)

- `TOOLS/SEARCH_CONSOLE/analise_vendas/` tem 2 scripts com entrypoint
  (`analise_organico.py` e `analise_tecnica.py`) — um `tool.json` por
  pasta e o padrao das outras 4 tools, entao nao da pra por os 2 no
  mesmo lugar. `analise_organico/tool.json` ficou junto do script
  (`TOOLS/SEARCH_CONSOLE/analise_vendas/`); `analise_tecnica/tool.json`
  foi pra uma pasta nova (`TOOLS/SEARCH_CONSOLE/analise_tecnica/`) sem
  mover o `.py` (que continua em `analise_vendas/`) — resolve o
  conflito sem mexer em import nenhum, mas fica com o `tool.json` e o
  script em pastas diferentes pra essa uma tool.
- IMPORTANTE: isso so cria a METADATA (`tool.json`), pra elas
  aparecerem no `discover_tool`/Redis. `agentes.py` e
  `orchestrator._executar_tool_leitura` AINDA NAO sabem executar
  `analise_ads`, `analise_organico` nem `analise_tecnica` — se o Claude
  chamar uma dessas 3, hoje cai no fallback "ferramenta desconhecida".
  Wiring de execucao fica pra uma tarefa separada.

## Fora de escopo aqui

Renomear as pastas (`TOOLS/ADWORDS/analise_vendas/` ->
`TOOLS/ADWORDS/analise_ads/` etc) pra tirar a confusao de nome de
pasta — mexe em imports/skills que apontam pro caminho atual, fica
pra uma tarefa separada se for decidido fazer.
