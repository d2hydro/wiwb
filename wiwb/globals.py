from shapely.geometry import Point, Polygon, MultiPolygon
from typing import Literal
import os

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

IMPLEMENTED_GEOMETRY_TYPES = [Point, Polygon, MultiPolygon]


class Defaults:
    bounds: tuple[float, float, float, float] = (109950, 438940, 169430, 467600)
    crs: int = 28992


def get_defaults(**kwargs):
    return Defaults(**kwargs)
