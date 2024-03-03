# %%
import pytest
from wiwb import Auth, Api
from geopandas import GeoSeries
from pandas import DataFrame
from pathlib import Path
import pandas as pd
from wiwb.constants import GEOSERIES, get_defaults

DIR = Path(__file__).parent.joinpath("data")


@pytest.fixture
def api() -> Api:
    return Api()


@pytest.fixture
def auth() -> Auth:
    return Auth()


@pytest.fixture
def geoseries() -> GeoSeries:
    return GEOSERIES


@pytest.fixture
def defaults():
    return get_defaults()


@pytest.fixture
def nc_df() -> DataFrame:
    df_expected = pd.read_csv(
        DIR.joinpath("test_sample_nc_dir.csv"),
        header=[0, 1],
        index_col=0,
        parse_dates=True,
    )
    return (df_expected * 100).astype(int)


@pytest.fixture
def grids_df() -> DataFrame:
    df_expected = pd.read_csv(
        DIR.joinpath("test_sample_grids.csv"),
        header=[0],
        index_col=0,
        parse_dates=True,
    )
    return (df_expected * 100).astype(int)


# %%
