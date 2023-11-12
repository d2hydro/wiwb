import numpy as np
from numpy import ndarray
from rasterstats import zonal_stats
from geopandas import GeoSeries
from affine import Affine
from typing import List, Union


def flatten_stats(stats_dict: List[str], stats: List[str]) -> List[float]:
    return np.array([[item[stat] for stat in stats] for item in stats_dict]).flatten()


def sample_geoseries(
    values: ndarray,
    geometries: Union[List, GeoSeries],
    affine: Affine,
    nodata: float,
    stats: List[str],
) -> List[float]:
    stats_dict = zonal_stats(
        geometries,
        values,
        affine=affine,
        nodata=nodata,
        stats=" ".join(stats),
        boundless=True,
    )

    return flatten_stats(stats_dict, stats)
