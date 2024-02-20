def test_data_sources(api):
    data_sources = api.get_data_sources()
    assert "Meteobase.Precipitation" in data_sources.keys()
