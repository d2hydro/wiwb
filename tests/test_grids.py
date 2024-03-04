# %%
from wiwb.api_calls import GetGrids
from datetime import date
import pytest


def test_grids(auth, api, tmp_path, geoseries, grids_df):
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

    # check if we have results and if they are as expected
    assert not df.empty
    assert (df * 100).astype(int).equals(grids_df)

    # check write to disck
    grids.to_directory(tmp_path)
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

    assert grids.geoseries.crs.to_epsg() == 28992


def test_bounds(auth, api, defaults):
    # init grids without bounds, should result in default bounds
    grids = GetGrids(
        auth=auth,
        base_url=api.base_url,
        data_source_code="Meteobase.Precipitation",
        variable_code="P",
        start_date=date(2018, 1, 1),
        end_date=date(2018, 1, 2),
        data_format_code="netcdf4.cf1p6",
    )

    assert grids.bbox == defaults.bounds

    # setting bounds to None should result in ValueError ("Specify either 'geometries' or 'bounds', both are None")
    with pytest.raises(
        ValueError, match="Specify either 'geometries' or 'bounds', both are None"
    ):
        grids.set_bounds(None)

    # setting geometries
    grids.set_geometries(defaults.geoseries)
    grids.set_bounds(None)

    assert grids.bbox == tuple(defaults.geoseries.total_bounds)
