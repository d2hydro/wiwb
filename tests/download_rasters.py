import os
import sys
import requests
from typing import Union, List
from dataclasses import dataclass
import base64
import jwt
from datetime import datetime, timedelta
from pathlib import Path
from shapely.geometry import Point, Polygon, box
from datetime import date
from geopandas import GeoSeries

wiwb_path = Path(__file__).parents[2]
sys.path.append(str(wiwb_path))
from wiwb import Auth, Api
from wiwb.api_calls import GetGrids

CLIENT_ID = os.getenv("wiwb_client_id")
API_URL = "https://wiwb.hydronet.com/api"
CRS_EPSG = 28992
DATA_FORMAT_CODE = dict(
    geotiff = "geotiff",
    aaigrid = "aaigrid",
    hdf5 = "hdf5",
    netcdf4 = "netcdf4.cf1p6",
    netcdf4_zip = "netcdf4.cf1p6.zip"
    )

OUTPUT_DIR = Path(__file__)
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
     crs=28992
     )

#% get authorization
auth = Auth()
assert auth.client_id == CLIENT_ID

#% init wiwb api
api = Api()
assert api.auth.client_id == CLIENT_ID

#% get data source codes
data_sources = api.get_data_sources()
assert "Meteobase.Precipitation" in data_sources.keys()

#% get variable codes
variables = api.get_variables(data_source_codes=["Meteobase.Precipitation"])
assert "P" in variables.keys()

#% get grids

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
df.to_csv("sample.csv")
GEOSERIES.to_file("geoseries.gpkg")
grids.write("")
