from datetime import date
from pathlib import Path

from wiwb.sample import sample_nc_dir

START_DATE = date(2015, 1, 1)
END_DATE = date(2015, 1, 2)
DIR = Path(__file__).parent.joinpath("data")
STATS = ["mean", "min", "max"]


def test_sample_nc_dir(geoseries, nc_df):
    variables = [i.name for i in DIR.glob(r"*/")]
    variable = variables[0]
    dir = DIR.joinpath(variable)

    df = sample_nc_dir(dir, variable, geoseries, STATS, START_DATE, END_DATE)

    assert not df.empty
    assert (df * 100).astype(int).equals(nc_df)
