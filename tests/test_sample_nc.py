from pathlib import Path
from datetime import date
from wiwb.sample import sample_nc_dir


START_DATE = date(2015, 1, 1)
END_DATE = date(2015, 1, 2)
DIR = Path(__file__).parent.joinpath("data")
STATS = ["mean"]


def test_sample_nc_dir(geoseries):
    variables = [i.name for i in DIR.glob(r"*/")]
    variable = variables[0]
    dir = DIR.joinpath(variable)

    df = sample_nc_dir(dir, variable, geoseries, STATS, START_DATE, END_DATE)

    assert not df.empty
