#%%
import xarray as xr
from pathlib import Path
import os
from shapely.geometry import Point, box
from geopandas import GeoSeries
from datetime import date
from wiwb.sample import sample_geoseries
import pandas as pd

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

start_date=date(2015,1,1)
end_date=date(2015,1,2)
geometries = GEOSERIES

variable_code = "DRZSM-AMSR2-C1N-DESC-T10_V003_100"
stats= ["mean"]

#%%
files = list(Path(r"d:\projecten\D2307.HDSR_FEWSPY\02.VdSatBodemvocht\voor_2020\DRZSM-AMSR2-C1N-DESC-T10_V003_100").glob("*.nc"))

ds = xr.open_mfdataset(files, decode_coords="all")
data = {}
# read all transforms to see if dataset is consistent   
transforms = list(set(xr.open_dataset(file).rio.transform() for file in files))
if len(transforms) == 1:
    affine = transforms[0]
else:
    raise ValueError(f"Files do not have one consistent transform. Got {transforms}")

#
#

# %%

for file in files:
    ds = xr.open_dataset(file, decode_coords="all").sel(time=slice(start_date, end_date))
    nodata = ds[variable_code].attrs.get("_FillValue")
    affine = ds.rio.transform()

    geometries = geometries.to_crs(ds.rio.crs)
    for time in ds["time"].values:
        data[time] =  sample_geoseries(
                values=ds[variable_code].sel(time=time).values,
                geometries=geometries,
                affine=affine,
                nodata=nodata,
                stats=stats,
            )


    columns = geometries.index

df = pd.DataFrame.from_dict(data, orient="index", columns=columns)
# %%
