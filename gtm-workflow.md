# Workflow — Auditoria de GTM

Este arquivo descreve como o agente deve se comportar quando o pedido for do tipo:

> "Faça uma auditoria no GTM da Integra Foods"

O objetivo é chegar num formato que vira uma **skill** do agente (não só um script solto) — o
usuário fala o nome do site, o agente resolve o resto sozinho.

---

## 1. Trigger

- "audita o GTM de [site]"
- "verifica se o GTM da [site] está bem configurado"
- "o GTM da [site] está publicado?"

## 2. Resolver o site → dados do container

Cada site precisa de um registro com os dados que o agente usa pra saber onde olhar. Para o
Integra Foods, hoje já sabemos (achado ao preencher o `pratico.md` e confirmado navegando
tagmanager.google.com em 22/07/2026):

**⚠️ Existem 2 containers GTM na conta Google ligados ao Integra Foods — não confundir:**

| Conta no GTM | Container | GTM ID | Status |
|---|---|---|---|
| **IF V2** | `ifv2.conge.digital` | `GTM-PJWJJHXR` | ✅ **É este que usamos** — o correto/ativo |
| Integra Foods | `www.integrafoods.ind.br` | `GTM-W6GWZX5` | 🗑️ **LEGADO — ignorar, não auditar** (confirmado pelo usuário) |

| Dado | Valor (Integra Foods — container correto `GTM-PJWJJHXR`) | Onde achamos |
|---|---|---|
| Container GTM | `GTM-PJWJJHXR` | `ssr-poc/src/config.js` |
| GTM accountId | `6363669174` | export do workspace / confirmado no GTM |
| GTM containerId | `257024578` | export do workspace / confirmado no GTM |
| Measurement ID GA4 | `G-CC4D18ST42` | tag "Google tag - GA4" no export do workspace |
| Export local de referência | `C:\INTEGRAFOODS\www\web2\IA\GTM-PJWJJHXR_workspace7.json` | achado no repo |

Isso deveria virar um registro central de sites (o `sites/<nome>/` mencionado no `brainstorm.md`,
§5), pra 3G Foods e Adoro terem o mesmo tipo de entrada quando chegar a vez deles.

## 3. Passos do workflow

1. Carregar as credenciais da GTM API (OAuth) para a conta que tem acesso ao container do site
2. Listar containers/workspaces via API e localizar o container pelo ID resolvido no passo 2
3. Comparar a versão **publicada (live)** com o **workspace/draft** — sinalizar se há mudanças
   pendentes de publicar
4. Rodar os checks de saúde (mesma lista do `brainstorm.md`, §2.1):
   - tags sem trigger associado
   - triggers apontando pra eventos que não existem mais
   - tag de conversão do Ads publicada na versão live
   - variáveis de dataLayer usadas nas tags batem com o que o site realmente dispara
5. (Opcional, decisão em aberto no brainstorm) navegar o site de verdade via browser automation
   pra capturar o `dataLayer` ao vivo e confirmar que os eventos disparam
6. Gerar o resultado: lista de achados, sem executar nenhuma mudança — auditoria é sempre leitura

## 4. Saída esperada

Um resumo estruturado, por exemplo:

```
Auditoria GTM — Integra Foods (GTM-PJWJJHXR)
- Versão live: v12 (publicada em 2026-06-10) | Workspace tem 2 mudanças não publicadas
- Tags: 5 ativas, 0 órfãs
- Tag GA4 (G-CC4D18ST42): publicada e disparando em todas as páginas
- Tag de e-commerce: cobre view_item e add_to_cart; purchase não encontrado — VERIFICAR
- Alertas: 1
```

## 5. O que falta implementar

- [ ] Credenciais/OAuth da GTM API para a conta que administra o `GTM-PJWJJHXR`
- [ ] Módulo que lê o container via API (equivalente ao `gtm_auditor.py` do `brainstorm.md`)
- [ ] Registro central de sites (container ID, measurement ID) — hoje só sabemos o do Integra Foods
- [ ] Decidir: auditoria só estática (ler config) ou também dinâmica (navegar o site)
- [ ] Formalizar isso como skill do agente, pra responder a "audita o GTM de X" sem eu precisar
      reexplicar o processo toda vez
