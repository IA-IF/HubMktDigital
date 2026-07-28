from consultar_schema import consultar_schema


def test_consultar_schema_devolve_campos_reais_de_campaign():
    resultado = consultar_schema("Campaign")
    nomes_campos = [f["name"] for f in resultado["fields"]]
    assert "campaign_budget" in nomes_campos
    assert "maximize_conversions" in nomes_campos
    assert resultado["name"].endswith("Campaign")


def test_consultar_schema_devolve_campos_de_proximity_info():
    resultado = consultar_schema("ProximityInfo")
    nomes_campos = [f["name"] for f in resultado["fields"]]
    assert "geo_point" in nomes_campos or "radius" in nomes_campos


def test_consultar_schema_erro_pra_tipo_desconhecido():
    resultado = consultar_schema("TipoQueNaoExiste123")
    assert "erro" in resultado
