# %%
import os
from typing import Literal

from geopandas import GeoSeries
from shapely.geometry import MultiPolygon, Point, Polygon, box

API_URL = "https://wiwb.hydronet.com/api"
AUTH_URL = (
    "https://login.hydronet.com/auth/realms/hydronet/protocol/openid-connect/token"
)

CLIENT_ID = os.getenv("wiwb_client_id")
CLIENT_SECRET = os.getenv("wiwb_client_secret")

FILE_SUFFICES = {
    "geotiff": "zip",
    "aaigrid": "hdf5",
    "hdf5": "hdf5",
    "netcdf4.cf1p6": "nc",
    "netcdf4.cf1p6.zip": "zip",
}

PRIMARY_STRUCTURE_TYPES = Literal[
    "EnsembleGrid",
    "EnsembleTimeSeries",
    "Event",
    "Grid",
    "ModelGrid",
    "ModelTimeSeries",
    "TimeSeries",
]

DATA_FORMAT_CODES = Literal[*FILE_SUFFICES.keys()]

IMPLEMENTED_GEOMETRY_TYPES = [Point, Polygon, MultiPolygon]

INTERVAL_TYPES = Literal["Days", "Hours", "Minutes"]

CRS_EPSG = 28992
LL_POINT = Point(119865, 449665)
UR_POINT = Point(127325, 453565)
OTHER_POINT = Point(135125, 453394)
POLYGON = box(LL_POINT.x, LL_POINT.y, UR_POINT.x, UR_POINT.y)
GEOSERIES = GeoSeries(
    [LL_POINT, UR_POINT, OTHER_POINT, POLYGON],
    index=["ll_point", "ur_point", "other_point", "polygon"],
    crs=CRS_EPSG,
)


class Defaults:
    bounds: tuple[float, float, float, float] = (109950, 438940, 169430, 467600)
    crs: int = 28992
    geoseries = GEOSERIES


def get_defaults(**kwargs):
    return Defaults(**kwargs)


# %%
