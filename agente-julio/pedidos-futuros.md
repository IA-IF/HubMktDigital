# Pedidos futuros do Julio

Coisas que o usuario pediu e o Julio ainda nao sabe fazer — registradas automaticamente pela ferramenta `registrar_pedido_futuro` em vez de inventar uma resposta. Revisar aqui e decidir juntos o que vira implementacao (nao e uma fila que se implementa sozinha).

## 2026-07-22 10:25 — Integra Foods
**Pedido:** Automatizar auditoria de tracking de e‑commerce para integrafoods.ind.br: executar checklist técnico (validar dataLayer/push de purchase, checar disparos GTM/GA4 em modo Preview/DebugView, verificar measurementId, detectar duplicidade de transaction_id, validar moeda/valor, e reconciliar pedidos GA x backend) e gerar relatório com falhas detectadas, impacto estimado e correções sugeridas.
**Contexto:** Requestor quer que as verificações listadas no checklist sejam feitas automaticamente. Observação prévia: nos últimos 7 dias GA mostrou 2 compras e receita R$2.418,20; ticket_medio retornado pela API estava inconsistente. Saída esperada: relatório detalhado (logs das transmissões, exemplos de eventos purchase, listagem de pedidos sem match, percentuais de cobertura, diferenças de receita) e steps práticos para correção. Recursos necessários: acesso GA4 (measurementId/property), acesso GTM (container), acesso ao backend/order exports (CSV com order_id, valor, data), credenciais/staging para reproduzir teste de checkout. Prazo esperado: 48-72h após disponibilização de acessos.

