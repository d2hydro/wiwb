def test_variable_codes(api):
    variables = api.get_variables(data_source_codes=["Meteobase.Precipitation"])
    assert "P" in variables.keys()
