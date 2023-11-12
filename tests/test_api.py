import os
from pathlib import Path
from shapely.geometry import Point, box
from datetime import date
from geopandas import GeoSeries
from wiwb import Auth, Api
from wiwb.api_calls import GetGrids
import pytest

CLIENT_ID = os.getenv("wiwb_client_id")
CRS_EPSG = 28992
LL_POINT = Point(119865,449665)
UR_POINT = Point(127325,453565)
OTHER_POINT = Point(135125,453394)
POLYGON = box(LL_POINT.x, LL_POINT.y, UR_POINT.x, UR_POINT.y)
GEOSERIES = GeoSeries(
    [LL_POINT,
     UR_POINT,
     OTHER_POINT,
     POLYGON],
     index=["ll_point", "ur_point", "other_point", "polygon"],
     crs=CRS_EPSG
     )


@pytest.fixture
def api():
    return Api()

@pytest.fixture
def auth():
    return Auth()

def test_authorization(auth):
    assert auth.client_id == CLIENT_ID

def test_wiwb_api(api):
    assert api.auth.client_id == CLIENT_ID

def test_data_sources(api):
    data_sources = api.get_data_sources()
    assert "Meteobase.Precipitation" in data_sources.keys()

def test_variable_codes(api):
    variables = api.get_variables(data_source_codes=["Meteobase.Precipitation"])
    assert "P" in variables.keys()

def test_grids(auth, api, tmp_path):

    """
    note WIWB does guarantee you get all data within bounds. Therefore other_point will be outside
    bounds and result is None :-(

    """
    grids = GetGrids(
        auth=auth,
        base_url=api.base_url,
        data_source_code="Meteobase.Precipitation",
        variable_code="P",
        start_date=date(2018,1,1),
        end_date=date(2018,1,2),
        data_format_code="netcdf4.cf1p6",
        geometries=GEOSERIES
    )

    df = grids.sample()
    assert not df.empty
    grids.write(tmp_path)
    assert (tmp_path.joinpath("Meteobase.Precipitation_P_2018-01-01_2018-01-02.nc").exists())
