# LEGADO

Movido pra cá em 2026-07-22: os 4 auditores (`agente-ads`, `agente-ga4`,
`agente-gtm`, `agente-search-console`), o orquestrador Telegram
(`agente-julio`) e a skill `skill-onboard-site` (antes em
`.claude/skills/onboard-site`). O usuário pretende substituir essa geração
de agentes por outra (provavelmente usando a infra Redis em `../REDIS/`) e
não tinha certeza se valia a pena continuar investindo nesta.

Todo código continua funcional como estava — os `config.py` resolvem
caminhos relativos ao próprio arquivo (`Path(__file__).resolve()...`), não
por caminho absoluto fixo, então sobreviveram à mudança de pasta sem
quebrar. Se decidir reativar em vez de substituir, é só rodar os `main.py`
normalmente daqui de dentro.

## Estado da consolidação de `.env` (interrompida no meio)

Estava em andamento uma limpeza dos ~17 arquivos `.env.<site>` que existiam
espalhados (um por módulo por site), porque muitos valores eram idênticos
entre os 3 sites (mesmo client OAuth do Google, mesmas chaves de LLM,
mesmo bot do Telegram). Ficou assim quando parou:

- **Feito**: criado `.env` compartilhado aqui em `LEGADO/.env` (+
  `.env.example`) com tudo que é comum aos 3 sites; criado
  `SITES/<site>/.env` (integrafoods, 3gfoods, adoro) só com o que é único
  por site (customer ID, property ID, container ID, site URL); template de
  onboarding em `SITES/_template/.env.example`; os 5 `config.py`
  atualizados para carregar `LEGADO/.env` + `LEGADO/SITES/<site>/.env`.
- **Não feito**: os `.env.<site>` antigos dentro de cada
  `agente-*/` (ex.: `agente-ads/.env.3gfoods`) ainda existem, sem uso —
  ninguém mais lê eles, mas não foram apagados. READMEs de cada módulo e
  `skill-onboard-site/SKILL.md` ainda descrevem o padrão antigo
  (`.env.<site>` dentro do próprio módulo), não o novo.
- Se este código for reativado, terminar isso é só apagar os
  `agente-*/.env.<site>` órfãos e atualizar os READMEs/skill pra descrever
  `LEGADO/.env` + `LEGADO/SITES/<site>/.env`. Se for descartado mesmo,
  ignora — não vale o esforço.
