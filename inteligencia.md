# Inteligência do agente conversacional — plano por etapa

Um registro curto por etapa discutida (ver `entendendno.md` pro traço
passo a passo H/I/P/R). Cada entrada aqui é a decisão de design que sai da
discussão, não a explicação didática.

## Etapa 1 — `/start` com seleção obrigatória de site

- Comando `/start` (funciona tanto no Telegram quanto no modo Python/CLI)
  responde com um menu numerado:
  ```
  selecione o site
  1 3gfoods
  2 adoro
  3 integrafoods
  ```
- Resposta é **obrigatória** — nenhuma outra ação roda antes de escolher
  uma opção válida (1, 2 ou 3).
- A opção escolhida define qual pasta de site o agente usa daqui pra
  frente na conversa: `C:\INTEGRAFOODS\teste\HubMktDigital\SITES`.
- Isso substitui/formaliza o `_detectar_site` por regex livre que o Julio
  usa hoje (`orchestrator.py`) — em vez de tentar casar apelido no texto
  livre, é sempre um menu fechado de 3 opções.

## Etapa 2 — `discover_tool` via busca vetorial no Redis

- O catálogo real de ferramentas não são as 3 de hoje (`consultar_trafego`,
  `propor_campanha`, `registrar_pedido_futuro`) — é o universo de métodos
  das APIs de GA4, GTM, Ads e Search Console (só GA4 já tem ~50 métodos
  catalogados em `agente-ga4/referencia-api.md`, 2 em uso). Mandar a
  descrição completa de dezenas/centenas de ferramentas em toda mensagem
  não escala (custo de token cresce, e o modelo erra mais com muita
  ferramenta parecida na mesma chamada).
- Solução: um passo de descoberta antes da chamada real ao Claude — busca
  vetorial (RedisVL, já é dependência do projeto via
  `SemanticMessageHistory`) sobre um catálogo de ferramentas indexado no
  Redis (embedding de nome+descrição de cada método/ferramenta).
- Fluxo por mensagem: (1) embeda a mensagem do usuário, (2) busca as
  top-K ferramentas mais próximas no Redis, (3) só essas K viram o
  `tools=[...]` daquela chamada ao Claude — nunca o catálogo inteiro.
- Trade-off aceito: mais uma etapa antes da chamada ao LLM (latência) e
  a necessidade de manter os embeddings do catálogo sincronizados quando
  uma ferramenta for adicionada/mudar de descrição.
- **Caso zero candidatos:** pra mensagem que não bate com nada relevante
  (ex: "oi"), a busca vetorial tem que saber devolver 0 resultados sem
  quebrar — nesse caso `tools=[]` (ou o parâmetro nem é mandado) naquela
  chamada, e o Claude responde em texto puro, sem opção de ferramenta
  nenhuma. Não forçar top-K fixo quando nada está acima do limiar de
  relevância.
- Mesmo padrão do `ToolSearch` usado pelo Claude Code nesta própria sessão
  (tools deferidas, schema completo só carregado sob demanda via busca) —
  não é uma ideia nova, é replicar algo que já funciona numa escala
  parecida.
