import numpy as np
from numpy import ndarray
from rasterstats import zonal_stats
from geopandas import GeoSeries
from affine import Affine
from typing import List, Union
import xarray
import pandas as pd
from pathlib import Path
from datetime import date


def flatten_stats(stats_dict: List[str], stats: List[str]) -> List[float]:
    return np.array([[item[stat] for stat in stats] for item in stats_dict]).flatten()


def sample_geoseries(
    values: ndarray,
    geometries: Union[List, GeoSeries],
    affine: Affine,
    nodata: float,
    stats: Union[str, List[str]] = "mean",
) -> List[float]:

    # we work with lists to flatten_stats
    if isinstance(stats, str):
        stats = [stats]

    stats_dict = zonal_stats(
        geometries,
        values,
        affine=affine,
        nodata=nodata,
        stats=" ".join(stats),
        boundless=True,
    )

    return flatten_stats(stats_dict, stats)


def sample_netcdf(
    nc_file: Path | str,
    variable_code: str,
    geometries: Union[List, GeoSeries],
    stats: Union[str, List[str]] = "mean",
    start_date: date | None = None,
    end_date: date | None = None,
    unlink: bool = False,
) -> pd.DataFrame:
    """Sample a set of geometries over a netcdf file

    Parameters
    ----------
    nc_file : Path or str
        path to NetCDF file
    variable_code : str
        Variable in NetCDF file to sample
    geometries : Union[List, GeoSeries]
        geometries to sample
    stats : List[str]
        statistics to sample
    start_date : date | None
        start date for selection, by default None
    end_date: date | None
        end date for selection, by default None
    unlink : bool, optional
        option to delete netcdf-file after sampling, by default False

    Returns
    -------
    pd.DataFrame
        Pandas DataFrame with statistics per timestamp per geometry
    """
    if isinstance(nc_file, str)
        nc_file = Path(str)
    assert nc_file.is_file(), f"nc_file {nc_file} does not exist"
    
    # read temp-source for sampling
    with xarray.open_dataset(nc_file, engine="netcdf4") as ds:
        if (start_date is not None) and (end_date is not None):
            ds = ds.sel(time=slice(start_date, end_date))
        nodata = ds[variable_code].attrs.get("_FillValue")
        affine = ds.rio.transform()
        data = {
            time: sample_geoseries(
                values=ds[variable_code].sel(time=time).values,
                geometries=geometries,
                affine=affine,
                nodata=nodata,
                stats=stats,
            )
            for time in ds["time"].values
        }

    # delete temp-file
    if unlink:
        if nc_file.exists():
            nc_file.unlink()

    # create columns
    if isinstance(stats, str):
        stats = [stats]

    if len(stats) == 1:
        columns = geometries.index
    else:
        geom_index = geometries.index
        columns = pd.MultiIndex.from_product(
            iterables=[geom_index, stats], names=["index", "stats"]
        )

    return pd.DataFrame.from_dict(data, orient="index", columns=columns)


def sample_netcdfs(
    nc_files: list[Path],
    variable_code: str,
    geometries: Union[List, GeoSeries],
    stats: Union[str, List[str]] = "mean",
    start_date: date | None = None,
    end_date: date | None = None,
):
    """Sample over a set of netcdf-files

    Parameters
    ----------
    nc_files : list[Path]
        A list of netcdf-files
    variable_code : str
        Variable in NetCDF file to sample
    geometries : Union[List, GeoSeries]
        geometries to sample
    stats : List[str]
        statistics to sample
    start_date : date | None
        start date for selection, by default None
    end_date: date | None
        end date for selection, by default None

    Returns
    ------
    pd.DataFrame
        Pandas DataFrame with statistics per timestamp per geometry
    """
    assert nc_files, f"no NetCDF files to sample"
    for nc_file in nc_files:
        assert nc_file.is_file(), f"nc_file {nc_file} does not exist"   

    # read all transforms to see if dataset is consistent
    transforms = list(
        set(xarray.open_dataset(file.as_posix()).rio.transform() for file in nc_files)
    )
    if len(transforms) == 1:
        with xarray.open_dataset(nc_files[0].as_posix(), decode_coords="all") as ds:
            geometries = geometries.to_crs(ds.rio.crs)
    else:
        raise ValueError(
            f"Files do not have one consistent transform. Got {transforms}"
        )

    dfs = [
        sample_netcdf(
            nc_file,
            variable_code,
            geometries,
            stats=stats,
            start_date=start_date,
            end_date=end_date,
            unlink=False,
        )
        for nc_file in nc_files
    ]
    dfs = [i for i in dfs if not i.empty]
    df = pd.concat(dfs).sort_index()

    return df


def sample_nc_dir(
    dir: Path | str,
    variable_code: str,
    geometries: Union[List, GeoSeries],
    stats: Union[str, List[str]] = "mean",
    start_date: date | None = None,
    end_date: date | None = None,
):
    """Sample over a directory of netcdf-files

    Parameters
    ----------
    dir_path : Path | str
        Directory with netcdf files
    variable_code : str
        Variable in NetCDF file to sample
    geometries : Union[List, GeoSeries]
        geometries to sample
    stats : List[str]
        statistics to sample
    start_date : date | None
        start date for selection, by default None
    end_date: date | None
        end date for selection, by default None

    Returns
    ------
    pd.DataFrame
        Pandas DataFrame with statistics per timestamp per geometry
    """
    if isinstance(dir_path, str):
        dir_path = Path(dir_path)
    assert dir_path.is_dir(), f"dir_path {dir_path} does not exist"
    
    nc_files = [x for x in dir_path.iterdir() if x.suffix == ".nc"]

    df = sample_netcdfs(
        nc_files,
        variable_code=variable_code,
        geometries=geometries,
        stats=stats,
        start_date=start_date,
        end_date=end_date,
    )
    return df
