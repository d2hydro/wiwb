# WIWB API
A Python API on the WIWB API. It includes:
- authorization
- get `datasources`
- get `variables`
- get `grids`
- sample `grids` to a set of geometries (points and/or polygons)


## Getting started
Request a wiwb client-id and client-secret. Provide them as `wiwb_client_id` and `wiwb_client_secret` os environment variables for your convenience. Alternatively it can be specified at init.

Import wiwb Api and Auth. GetGrids is not implemented in the Api module (yet) so we import it seperately

```
from wiwb import Auth, Api
from wiwb.api_calls import GetGrids
```

## Get sources

Find data_sources. You'll notice `Meteobase.Precipitation` being one of them

```
data_sources = api.get_data_sources()
```

## Get variables
Find variables under `Meteobase.Precipitation`. You'll notice `P` being the only variable:

```
variables = api.get_variables(
    data_source_codes=["Meteobase.Precipitation"]
    )
```

## Get grids
We'll specify a download for WIWB MeteoBase Precipitation. If we don't specify a `bounds` or `geometries`, `GetGrids` will be set for the extent of Water Authority HDSR.

```
grids = GetGrids(
    auth=auth,
    base_url=api.base_url,
    data_source_code="Meteobase.Precipitation",
    variable_code="P",
    start_date=date(2018,1,1),
    end_date=date(2018,1,2),
    data_format_code="netcdf4.cf1p6",
)
```

We can write the grids to an output directory. If we don't call `grids.run()` before, it will first request the data at WIWB:

```
grids.write(output_dir="")
```

## Sample grids
Let's sample the grids. We'll first make some geometries and assign it to `grids`:

```
from geopandas import GeoSeries
from shapely.geometry import Point, box

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

grids.geometries = GEOSERIES
```

Now we sample on geometries. We'll write the result to a CSV.

```
df = grids.sample()
df.to_csv("samples.csv")
```
