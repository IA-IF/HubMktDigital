from mutate import aplicar_campos, montar_mutate_operation, nome_campo_operacao


def test_nome_campo_operacao_simples():
    assert nome_campo_operacao("Campaign") == "campaign_operation"


def test_nome_campo_operacao_composto():
    assert nome_campo_operacao("CampaignCriterion") == "campaign_criterion_operation"
    assert nome_campo_operacao("AdGroupAd") == "ad_group_ad_operation"
    assert nome_campo_operacao("UserList") == "user_list_operation"


def test_montar_mutate_operation_campaign_forca_paused_mesmo_se_pedido_enabled():
    campos = {"name": "Teste", "advertising_channel_type": "SEARCH", "status": "ENABLED"}
    mutate_op = montar_mutate_operation("Campaign", "create", campos)
    assert mutate_op.campaign_operation.create.status.name == "PAUSED"
    assert mutate_op.campaign_operation.create.name == "Teste"


def test_montar_mutate_operation_campaign_forca_paused_quando_omitido():
    campos = {"name": "Teste"}
    mutate_op = montar_mutate_operation("Campaign", "create", campos)
    assert mutate_op.campaign_operation.create.status.name == "PAUSED"


def test_montar_mutate_operation_outro_recurso_nao_forca_status():
    campos = {"keyword": {"text": "patinho cubo", "match_type": "BROAD"}}
    mutate_op = montar_mutate_operation("AdGroupCriterion", "create", campos)
    criacao = mutate_op.ad_group_criterion_operation.create
    assert criacao.keyword.text == "patinho cubo"
    # guardrail de status=PAUSED e so pra Campaign -- outro recurso nao tem status forcado
    assert criacao.status.name == "UNSPECIFIED"


def test_aplicar_campos_dict_aninhado_vira_submensagem():
    from google.ads.googleads.v24.resources.types.ad_group_criterion import AdGroupCriterion
    criterio = AdGroupCriterion()
    aplicar_campos(criterio, {"keyword": {"text": "patinho cubo", "match_type": "BROAD"}})
    assert criterio.keyword.text == "patinho cubo"
    assert criterio.keyword.match_type.name == "BROAD"
