from wiwb.api_calls import GetGrids
from datetime import date


def test_grids(auth, api, tmp_path, geoseries):
    """
    note WIWB does guarantee you get all data within bounds. Therefore other_point will be outside
    bounds and result is None :-(

    """
    grids = GetGrids(
        auth=auth,
        base_url=api.base_url,
        data_source_code="Meteobase.Precipitation",
        variable_code="P",
        start_date=date(2018, 1, 1),
        end_date=date(2018, 1, 2),
        data_format_code="netcdf4.cf1p6",
        geometries=geoseries,
    )

    df = grids.sample()
    assert not df.empty
    grids.write(tmp_path)
    assert tmp_path.joinpath(
        "Meteobase.Precipitation_P_2018-01-01_2018-01-02.nc"
    ).exists()


def test_reproject(auth, api, geoseries):
    """
    note WIWB does guarantee you get all data within bounds. Therefore other_point will be outside
    bounds and result is None :-(

    """
    geoseries = geoseries.copy()

    # assume we provide in lat-lon
    geoseries = geoseries.to_crs(4326)
    assert geoseries.crs.to_epsg() == 4326

    # see if geoseries are reprojected at init
    grids = GetGrids(
        auth=auth,
        base_url=api.base_url,
        data_source_code="Meteobase.Precipitation",
        variable_code="P",
        start_date=date(2018, 1, 1),
        end_date=date(2018, 1, 2),
        data_format_code="netcdf4.cf1p6",
        geometries=geoseries,
    )

    assert grids.geometries.crs.to_epsg() == 28992

    # assume we have no crs in geometries and no epsg provided, this should raise a ValueError
    geoseries.crs = None
    try:
        grids = GetGrids(
            auth=auth,
            base_url=api.base_url,
            data_source_code="Meteobase.Precipitation",
            variable_code="P",
            start_date=date(2018, 1, 1),
            end_date=date(2018, 1, 2),
            data_format_code="netcdf4.cf1p6",
            geometries=geoseries,
            epsg=None,
        )
        assert False
    except ValueError:
        assert True
