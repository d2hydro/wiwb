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
from wiwb.auth import Auth
from wiwb.api_calls.body import RequestBody, ReaderSettings, Interval, Extent, Exporter, Reader
from wiwb.constants import (
    DATA_FORMAT_CODES,
    FILE_SUFFICES,
    INTERVAL_TYPES,
    get_defaults,
)
from wiwb.converters import rename_file
from wiwb.sample import sample_netcdf
import zipfile

logger = logging.getLogger(__name__)
defaults = get_defaults()

# @dataclass
class GetGrids(Request):
    """GetGrids request"""

    def __init__(
            self,
            auth: Auth,
            base_url: str,
            data_source_code: str,
            variable_code:str,
            start_date: date,
            end_date:date,
            unzip: bool=True,
            interval:Tuple[str, int] = ("Hours", 1),
            data_format_code: DATA_FORMAT_CODES = "geotiff",
            geometries: Union[GeoSeries, Iterable[Union[Point, Polygon, MultiPolygon]] | None] = None,
            bounds: Union[Tuple[float, float, float, float] |  None] = None
            ):

        # init from Requests class
        super().__init__(auth=auth, base_url=base_url)
    
        # GetGrids fields
        self.data_source_code: str = data_source_code
        self.variable_code:str = variable_code
        self.start_date: date = start_date
        self.end_date:date = end_date
        self.unzip: bool = unzip
        self.interval:Tuple[str, int] = interval
        self.data_format_code: DATA_FORMAT_CODES = data_format_code

        # hidden variables
        self._response: Union[requests.Response, None] = None
        self._geoseries: Union[GeoSeries, None] = None
        self._bounds: Union[Tuple[float, float, float, float], None] = field(
            init=False, default=None
        )

        # Set geometries and calculate bounds
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
                self.start_date.strftime('%Y%m%dT%H%M%S'),
                self.end_date.strftime('%Y%m%dT%H%M%S'),
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
    
    @property
    def bounds(self) -> Tuple[float, float, float, float]:
        return self._get_bounds(self._bounds)

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

    def set_bounds(self, bounds: Tuple[float, float, float, float] | None) -> None:
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

    def to_directory(self, output_dir: Union[str, Path], unzip:bool=False, rename_map:dict| None = None):
        """Write response.content to an output-file"""
        if self._response is None:
            self.run()

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        if unzip:

            # write content in temp_file
            temp_file = self.write_tempfile()

            with zipfile.ZipFile(temp_file, "r") as zf:
                for info in zf.infolist():
                    if info.is_dir():
                        continue

                    file_name = info.filename
                    if rename_map is not None:
                        file_name= output_dir / rename_file(file_name, **rename_map)
                    target = output_dir / file_name

                    # Schrijf binaire inhoud veilig weg
                    with zf.open(info, "r") as src, open(target, "wb") as dst:
                        while True:
                            chunk = src.read(1024 * 1024)
                            if not chunk:
                                break
                            dst.write(chunk)

        else:
            output_file = output_dir / self.file_name
            output_file.write_bytes(self._response.content)
