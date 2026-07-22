# HubMktDigital

Agente de IA para marketing digital de 3 e-commerces de proteína/alimentos
(Integra Foods, 3G Foods, Adoro). Foco: Google Ads + GTM + GA4 — auditar
contas existentes, propor e aplicar mudanças.

Histórico bruto do pedido original, IDs de conta (GTM/GA4/Ads/Search
Console) e credenciais de referência: ver `mydata.md` (gitignored, não
versionar).

## Estrutura

- `LEGADO/` — primeira geração de agentes (auditores GTM/GA4/Search
  Console/Ads + orquestrador Telegram `agente-julio`), movida pra cá em
  2026-07-22. Código funcional, mas será substituída — ver
  `LEGADO/README.md` antes de decidir reativar ou descartar.
- `REDIS/` — infra de memória de agente (Redis Cloud) + docs oficiais em
  `REDIS/DOCS/`; é a base cogitada para a próxima geração dos agentes.
- `pratico.md` — dados práticos das plataformas por site.
- `brainstorm.md` — ideias de arquitetura do agente.

## Regras

- **Site sempre explícito na conversa** — nunca auto-descoberta/inferência
  de qual site está em jogo.
- **Segredos só em `.env` gitignored** — nunca em CLAUDE.md, docs ou
  commits.
- **Plugins instalados devem ser usados sempre que forem relevantes**, não
  só instalados. Lista e status em `REDIS/plugins.md`.
