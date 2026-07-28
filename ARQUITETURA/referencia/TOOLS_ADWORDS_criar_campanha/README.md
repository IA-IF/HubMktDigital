# Referência — `criar_campanha` (retirado do catálogo ativo)

Movido pra cá em 2026-07-27, superado pelos executores genéricos
`TOOLS/ADWORDS/ads_consultar_schema` + `TOOLS/ADWORDS/ads_mutate` — ver
`docs/superpowers/specs/2026-07-27-execucao-generica-apis-design.md` e
`ARQUITETURA/contrato-tool-agente.md` (motivo: tool monolítica, uma
chamada atômica fazendo orçamento+campanha+bidding+targeting+grupo+
keywords+anúncio, incapaz de cobrir requisitos abertos como
segmentação por proximidade ou audiências customizadas sem código novo
a cada caso).

Fica aqui como referência — não como código morto esquecido. Não é
importado nem executado por nada; se algo aqui for útil de novo (ex:
lógica de conversão BRL→micros em `validacao.py`), copie o trecho pra
onde for usar, não reative este diretório.
