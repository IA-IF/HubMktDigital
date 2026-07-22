# Workflow — Verificação de acesso guiada (Playwright)

Padrão para quando o agente precisa checar ou conceder acesso administrativo
num console do Google que exige login humano (GTM, GA4, Search Console, Ads).
É a versão "ao vivo" das Fases burocráticas que já aparecem nos guias por
plataforma (ex: Fase 1 do `guia-agente-cmo-google-ads.md`) — em vez de eu só
te dar um checklist de texto, eu navego a tela junto com você.

## Quando usar

Sempre que um passo do tipo "confirme em [console] que a conta X tem acesso
a Y" aparecer no `pratico.md` ou no README de algum módulo (`agente-gtm`,
futuros `agente-ga4`, `agente-search-console`, etc.).

## Passos do padrão

1. **Eu abro o navegador** na URL do console (`tagmanager.google.com`,
   `analytics.google.com`, `search.google.com/search-console`,
   `ads.google.com`).
2. **Você faz o login manualmente** — eu nunca peço, digito ou manuseio
   credenciais/senhas/2FA.
3. Você avisa quando terminar o login.
4. **Eu navego** (via snapshot da página, não screenshot cego) até a tela
   relevante — normalmente Admin/Configurações → Usuários e permissões.
5. **Eu leio o estado atual** e reporto: quem já tem acesso, o que falta.
6. Se precisar de uma ação (adicionar usuário, conceder permissão), **eu
   descrevo exatamente o que vou clicar/preencher antes de fazer** — ações
   administrativas que concedem acesso não são reversíveis de graça, então
   sempre peço confirmação antes.
7. Registro o resultado no checklist da plataforma correspondente
   (`pratico.md` ou `docs/` do módulo).

## Onde isso vai se repetir

- **GTM** — container do Integra Foods agora; depois 3G Foods e Adoro
- **GA4** — Admin → Acesso à propriedade
- **Search Console** — Configurações → Usuários e permissões
- **Ads** — já foi feito manualmente pra 3G Foods (ver
  `agente-cmo/docs/setup-do-zero-checklist.md`); vai repetir pro Integra Foods
