import logging
import tempfile
from dataclasses import InitVar, dataclass, field
from datetime import date
from pathlib import Path
from typing import Iterable, List, Optional, Tuple, Union

import pyproj
import requests
from geopandas import GeoSeries
from pandas import DataFrame
from shapely.geometry import MultiPolygon, Point, Polygon

from wiwb.api_calls import Request
from wiwb.api_calls.body import RequestBody, ReaderSettings, Interval, Extent, Exporter, Reader
from wiwb.constants import (
    DATA_FORMAT_CODES,
    FILE_SUFFICES,
    INTERVAL_TYPES,
    get_defaults,
)
from wiwb.converters import snake_to_pascal_case
from wiwb.sample import sample_netcdf

logger = logging.getLogger(__name__)
defaults = get_defaults()

@dataclass
class GetGrids(Request):
    """GetGrids request"""

    data_source_code: str
    variable_code: str
    start_date: date
    end_date: date
    unzip: bool = True
    interval: Tuple[str, int] = ("Hours", 1)
    data_format_code: DATA_FORMAT_CODES = "geotiff"
    geometries: InitVar[Union[
        GeoSeries, Iterable[Union[Point, Polygon, MultiPolygon]], None
    ]] = None
    bounds: InitVar[Union[Tuple[float, float, float, float], None]] = defaults.bounds

    _response: Union[requests.Response, None] = field(
        init=False, default=None, repr=False
    )
    _geoseries: int = field(init=False, default=None)
    _bounds: Union[Tuple[float, float, float, float], None] = field(
        init=False, default=None
    )

    def __post_init__(self, geometries, bounds):
        self.set_geometries(geometries)
        self.set_bounds(bounds)

    @property
    def epsg(self):
        return defaults.crs

    @property
    def crs(self):
        return self.body.readers[0].settings.extent.crs

    @property
    def body(self) -> RequestBody:
        reader_settings = ReaderSettings(
            start_date=self.start_date,
            end_date=self.end_date,
            variable_codes=[self.variable_code],
            interval=Interval(*self.interval),
            extent=Extent(*self.bounds),
        )

        reader = Reader(self.data_source_code, settings=reader_settings)

        exporter = Exporter(data_format_code=self.data_format_code)

        return RequestBody(readers=[reader], exporter=exporter)

    @property
    def bbox(self):  # noqa:F811
        return self._bounds

    @property
    def file_name(self):
        stem = "_".join(
            [
                self.data_source_code,
                self.variable_code,
                self.start_date.isoformat(),
                self.end_date.isoformat(),
            ]
        )
        suffix = FILE_SUFFICES[self.data_format_code]
        return f"{stem}.{suffix}"

    @property
    def geoseries(self) -> GeoSeries:
        return self._geoseries

    @property
    def url_post_fix(self) -> str:
        return "grids/get"

    def _to_geoseries(
        self,
        geometries: Optional[Union[GeoSeries, Iterable[Union[Point, Polygon, MultiPolygon]]]],
    ) -> GeoSeries:

        # convert iterable to GeoSeries
        if geometries is not None:
            if not isinstance(geometries, GeoSeries):
                geometries = GeoSeries(geometries)

            # Check if geometries are Point, Polygon, or MultiPolygon
            if not all(
                (
                    i in ["Point", "Polygon", "MultiPolygon"]
                    for i in geometries.geom_type
                )
            ):
                raise ValueError(
                    f"Geometries must be Point, Polygon, or MultiPolygon, got {geometries.geom_type.unique()}"
                )

        geometries = self._reproject_geoseries(geoseries=geometries)
        return geometries

    def _reproject_geoseries(self, geoseries: GeoSeries) -> GeoSeries:
        """Set or reproject geoseries to self.epsg"""
        if geoseries.crs is None:
            logger.warning(f"no crs specified in geoseries, will be set to {self.epsg}")
            geoseries.crs = self.epsg
        else:
            geoseries = geoseries.to_crs(self.epsg)
        return geoseries

    def _get_bounds(self, bounds: Union[Tuple[float, float, float, float], None]):
        if (
            self._geoseries is not None
        ):  # if geometries are specified, we'll get bounds from geometries
            bounds = tuple(self._geoseries.total_bounds)
            if bounds is None:
                logger.warning(
                    "bounds will be ignored as long as geometries are not None"
                )
        elif bounds is None:  # if geometries aren't specified, user has to set bounds
            raise ValueError(
                """Specify either 'geometries' or 'bounds', both are None"""
            )
        return bounds

    def run(self):
        self._response = None
        self._response = requests.post(
            self.url, headers=self.auth.headers, json=self.body.json()
        )

        if not self._response.ok:
            self._response.raise_for_status()

    def set_geometries(
        self,
        geometries: Optional[Union[GeoSeries, Iterable[Union[Point, Polygon, MultiPolygon]]]],
    ) -> None:
        """Set a list or GeoSeries with Point, Polygon or MultiPolygon values. Handles conversion to
        GeoSeries and reprojection

        Parameters
        ----------
        geometries : GeoSeries, Iterable[Union[Point, Polygon, MultiPolygon]]
            A list or GeoSeries with Point, Polygon and Multipolygon objects
        """
        if geometries is not None:
            geoseries = self._to_geoseries(geometries)
            self._geoseries = geoseries
        else:
            self._geoseries = geometries

    def set_bounds(self, bounds: Tuple[float, float, float, float]) -> None:
        """Set new bounds values. Fits bounds to geoseries.bounds

        Parameters
        ----------
        bounds : Tuple[float, float, float, float]
            Bounds tuple

        """

        bounds = self._get_bounds(bounds)
        self._bounds = bounds

    def write_tempfile(self):
        with tempfile.NamedTemporaryFile(
            suffix=FILE_SUFFICES[self.data_format_code], delete=False
        ) as tmp_file:
            tmp_file_path = Path(tmp_file.name)
            tmp_file.write(self._response.content)
        return tmp_file_path

    def sample(self, stats: Union[str, List[str]] = "mean") -> DataFrame:
        """Sample statistics per geometry

        Parameters
        ----------
        stats : Union[str, List[str]]
            statistics to sample, provided as list of statistics or a string with one statistic. defaults to mean

            All stats in rasterstats.zonal_stats are available: https://pythonhosted.org/rasterstats/manual.html#statistics
            Common values are:
                - mean: average value of all cells in polygon
                - max: maximum value of all cells in polygon
                - min: minimum value of all cells in polygon
                - percentile_#: percentile value of all cells in polygon. E.g. percentile_50, gives 50th percentile (median) value

            Notes:
            - Providing multiple values, will create a multi-index column in your dataframe
            - Providing multiple statistics, as specified above, doesn't make much sense as it will always return the same value
        """  # noqa:E501

        # check if geometries are set
        if self._geoseries is None:
            raise TypeError(
                """'geometries' is None, should be list or GeoSeries. Set it first"""
            )

        # check if data_format_code is netcdf
        if self.data_format_code != "netcdf4.cf1p6":
            self.data_format_code = "netcdf4.cf1p6"
            self.run()

        # re-run
        if self._response is None:
            self.run()

        # write content in temp-file
        temp_file = self.write_tempfile()

        # sample temp_file
        df = sample_netcdf(
            nc_file=temp_file,
            variable_code=self.variable_code,
            geometries=self.geoseries,
            stats=stats,
            unlink=True,
        )

        return df

    def to_directory(self, output_dir: Union[str, Path]):
        """Write response.content to an output-file"""
        if self._response is None:
            self.run()

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / self.file_name
        output_file.write_bytes(self._response.content)
