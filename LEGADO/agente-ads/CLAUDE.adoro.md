# Contexto do Negócio

- Ecommerce de alimentos, site https://loja.adoro.com.br/ — conta Google Ads "Loja Adoro"
  (`510-339-3778`, já existente, MCC 890-192-5637) — **ajuste ticket médio e margem abaixo**
- Ticket médio: R$ 150 (AJUSTAR)
- Margem bruta: 40% (AJUSTAR)
- ROAS mínimo aceitável: 4.0 (breakeven em 2.5)
- Orçamento mensal total: R$ 10.000 (AJUSTAR)

# Regras de Decisão

- Pausar palavras-chave com gasto > R$ 50 e 0 conversões nos últimos 14 dias
- Aumentar orçamento (máx +20%/dia) em campanhas com ROAS > 6
- Reduzir lances em termos com CPA acima de R$ 60 (AJUSTAR)
- NUNCA alterar orçamento total em mais de 15% por dia
- NUNCA criar campanhas novas sem aprovação humana
- NUNCA reativar campanhas/keywords pausadas por humanos

# Limites de Segurança (guardrails invioláveis)

Estes limites também são validados em código pelo `executor.py` — os valores
efetivos vêm do `.env.adoro` (o modelo recomenda, o código impõe):

- Teto de gasto diário: R$ 500 (`TETO_GASTO_DIARIO`)
- Toda mudança com impacto estimado > R$ 100/dia exige aprovação humana (`LIMITE_APROVACAO_DIARIO`)
- Variação máxima de orçamento por campanha: 20%/dia (`MAX_MUDANCA_ORCAMENTO_PCT`)
- Ações permitidas ao agente: `pausar_keyword`, `ajustar_lance`, `ajustar_orcamento`, `negativar_termo`
- Qualquer outra ação vai automaticamente para a fila de aprovação

# Formato de Saída Esperado do Analista

O módulo `analyst.py` exige JSON estruturado com a lista `acoes`, cada uma com:
`acao`, `tipo_entidade`, `id_entidade`, `nome_entidade`, `valor_atual`,
`valor_novo`, `justificativa`, `impacto_estimado_diario_brl`.
