import pytest
from wiwb import Auth, Api
from geopandas import GeoSeries
from shapely.geometry import Point, box


@pytest.fixture
def api() -> Api:
    return Api()


@pytest.fixture
def auth() -> Auth:
    return Auth()


@pytest.fixture
def geoseries() -> GeoSeries:
    CRS_EPSG = 28992
    LL_POINT = Point(119865, 449665)
    UR_POINT = Point(127325, 453565)
    OTHER_POINT = Point(135125, 453394)
    POLYGON = box(LL_POINT.x, LL_POINT.y, UR_POINT.x, UR_POINT.y)
    return GeoSeries(
        [LL_POINT, UR_POINT, OTHER_POINT, POLYGON],
        index=["ll_point", "ur_point", "other_point", "polygon"],
        crs=CRS_EPSG,
    )
