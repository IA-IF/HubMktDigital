# Pedidos futuros do Julio

Coisas que o usuario pediu e o Julio ainda nao sabe fazer — registradas automaticamente pela ferramenta `registrar_pedido_futuro` em vez de inventar uma resposta. Revisar aqui e decidir juntos o que vira implementacao (nao e uma fila que se implementa sozinha).

## 2026-07-22 10:25 — Integra Foods
**Pedido:** Automatizar auditoria de tracking de e‑commerce para integrafoods.ind.br: executar checklist técnico (validar dataLayer/push de purchase, checar disparos GTM/GA4 em modo Preview/DebugView, verificar measurementId, detectar duplicidade de transaction_id, validar moeda/valor, e reconciliar pedidos GA x backend) e gerar relatório com falhas detectadas, impacto estimado e correções sugeridas.
**Contexto:** Requestor quer que as verificações listadas no checklist sejam feitas automaticamente. Observação prévia: nos últimos 7 dias GA mostrou 2 compras e receita R$2.418,20; ticket_medio retornado pela API estava inconsistente. Saída esperada: relatório detalhado (logs das transmissões, exemplos de eventos purchase, listagem de pedidos sem match, percentuais de cobertura, diferenças de receita) e steps práticos para correção. Recursos necessários: acesso GA4 (measurementId/property), acesso GTM (container), acesso ao backend/order exports (CSV com order_id, valor, data), credenciais/staging para reproduzir teste de checkout. Prazo esperado: 48-72h após disponibilização de acessos.

## 2026-07-22 10:59 — Integra Foods
**Pedido:** Auditoria de rastreamento do site https://integrafoods.ind.br — verificar implementação de e‑commerce no Google Analytics, eventos de compra, tags/GTAG/Google Tag Manager, possíveis tags duplicadas, UTM/tagging de campanhas pagas, configuração de conversões no Google Ads e atribuição de receita.
**Contexto:** Dados recentes mostram 140 sessões e 2 compras (R$2.418,20) nos últimos 7 dias, com toda a receita atribuída ao canal Direct — possível problema de tagging/atribuição. Usuário solicitou iniciar auditoria (opção A).

## 2026-07-22 11:02 — Integra Foods
**Pedido:** Verificar indexação das páginas do site https://integrafoods.ind.br — checar sitemap.xml, robots.txt, status HTTP (200/301/404), meta robots (noindex), tags canonical, cobertura no Google Search Console (páginas indexadas vs. excluídas), e listar páginas importantes (home, categorias, top produtos) que não estiverem indexadas com possíveis causas e recomendações.
**Contexto:** Solicitado após proposta de campanha; busca garantir que páginas chave estejam indexáveis antes/escalonamento de tráfego pago. Dados anteriores mostram possíveis problemas de tracking/atribuição; registrar auditoria separada já foi feito.

## 2026-07-22 11:44 — 3G Foods
**Pedido:** Validar e configurar rastreamento de conversões (GA4 e Google Ads) e testes end-to-end
**Contexto:** Conta: 3G Foods — site https://loja.3gfoods.com.br/. Dados iniciais: GA4 property properties/514973832. Google Ads account 758-019-9564 (MCC 890-192-5637). Escopo da tarefa: 1) Verificar que GA4 tem e-commerce habilitado e eventos purchase, add_to_cart, begin_checkout; 2) Validar que a tag do Google Ads está instalada e que há uma ação de conversão 'purchase' com envio de valor e moeda corretos; 3) Confirmar linkagem entre GA4 e Google Ads e configuração de importação de conversões; 4) Testes end-to-end (simular compra de teste e validar chegada do evento em GA4 e Google Ads); 5) Corrigir discrepâncias e reportar passos realizados; 6) Entregar checklist e evidências (prints / logs). Prioridade: alta. Prazo sugerido: 48 horas. Responsável de contato: Julio (marketing 3G Foods).
**Status (22/07/2026):** Diagnóstico (itens 1-3) feito — ver `../pratico.md`, seção 3G Foods.
Achados: GA4 confirma tracking real funcionando (2 compras/7 dias); **2 contas Ads linkadas** ao
GA4 (uma delas desconhecida, `7466004393`); ação de conversão "Adicionar ao carrinho" configurada
incorretamente pra contar `remove_from_cart`; 9 eventos não-comerciais contando pra smart bidding.
Itens 4-5 (teste end-to-end de compra real, correção das ações de conversão) **não feitos** —
exigem decisão humana (compra real tem efeito no sistema de fulfillment; corrigir conversão muda
sinal de otimização ativa).

## 2026-07-22 11:49 — 3G Foods
**Pedido:** Criar 2–3 landing pages de teste (variações: produto, categoria, oferta/CTA) para campanhas de Google Ads
**Contexto:** Conta: 3G Foods — site https://loja.3gfoods.com.br/. Requisito: 3 landings: 1) landing produto (foco em SKU principal), 2) landing categoria (suplementos/proteínas), 3) landing oferta (cupom/CTA forte). Incluir variações de título, hero, botão CTA e prova social. Prioridade: alta. Prazo sugerido: 72 horas. Entregáveis: URLs publicadas, brief de variações, checklist de implementação de pixels/tags. Contato: Julio (marketing 3G Foods).

## 2026-07-22 11:53 — 3G Foods
**Pedido:** Verificação fina e ajuste da integração GA4 → Google Ads (importação de evento 'purchase' como conversão, valores/moeda, e testes end‑to‑end)
**Contexto:** Conta: 3G Foods — site https://loja.3gfoods.com.br/. Informações: GA4 property properties/514973832; Google Ads account 758-019-9564 (MCC 890-192-5637). Escopo: 1) Confirmar que evento 'purchase' existe no GA4 e reporta receita; 2) Confirmar linkagem GA4↔Google Ads; 3) Importar evento purchase para Google Ads se não importado; 4) Validar que a ação de conversão no Ads registra valor (BRL) e está ativa; 5) Realizar testes end‑to‑end (compra de teste) e registrar logs/evidências; 6) Corrigir mapeamentos ou instruir dev sobre correções de tag; 7) Entregar checklist e evidências (prints/logs). Prioridade: alta. Prazo sugerido: 24–48 horas. Contato: Julio (marketing 3G Foods).
**Status (22/07/2026):** Mesmo diagnóstico do pedido das 11:44 (ver acima e `../pratico.md`) — a
ação de conversão "Compra" já existe, está ativa e importa valor/moeda corretamente (item 4 ok).
Itens 5-6 (teste end-to-end, correção de mapeamento incorreto do remove_from_cart) pendentes de
decisão humana.

