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
class Extent:
    f"""Extent for Settings in request body in correct epsg: {defaults.crs}.

    Parameters
    ----------
    xll : float
        The x-coordinate of the lower-left corner of the extent. Defaults to {defaults.bounds[0]}.
    yll : float
        The y-coordinate of the lower-left corner of the extent. Defaults to {defaults.bounds[1]}.
    xur : float
        The x-coordinate of the upper-right corner of the extent. Defaults to {defaults.bounds[2]}.
    yur : float
        The y-coordinate of the upper-right corner of the extent. Defaults to {defaults.bounds[3]}.
    """

    xll: float = defaults.bounds[0]
    yll: float = defaults.bounds[1]
    xur: float = defaults.bounds[2]
    yur: float = defaults.bounds[3]

    def __post_init__(self):
        if self.width <= 0:
            raise ValueError(
                f"'xll' ({self.xll}) should be smaller than 'xur' ({self.xur})"
            )

        if self.height <= 0:
            raise ValueError(
                f"'yll' ({self.yll}) should be smaller than 'yur' ({self.yur})"
            )

        self.correct_bounds()

    @property
    def width(self):
        return self.xur - self.xll

    @property
    def height(self):
        return self.yur - self.yll

    @property
    def crs(self):
        return pyproj.CRS(self.epsg)

    @property
    def epsg(self):
        return defaults.crs

    @property
    def spatial_reference(self):
        return {"Epsg": self.epsg}

    def correct_bounds(self):
        # get crs-unit
        units = None
        crs_dict = self.crs.to_dict()
        if "unit" in crs_dict.keys():
            units = crs_dict["units"]

        # get min width and height
        if units == "m":
            min_width_height = 10
        else:
            min_width_height = 0.0001  # we assume degrees

        # alter bounds
        if self.width < min_width_height:
            logger.warning(
                f"""Width of bounds < min_width ({self.width < min_width_height}). {self.xll} and {self.xur} will be adjusted"""  # noqa:E501
            )
            self.xll -= (min_width_height - self.width) / 2
            self.xur += (min_width_height - self.width) / 2

        if self.height < min_width_height:
            logger.warning(
                f"""Height of bounds < min_height ({self.height < min_width_height}). {self.yll} and {self.yur} will be adjusted"""  # noqa:E501
            )
            self.yll -= (min_width_height - self.height) / 2
            self.yur += (min_width_height - self.height) / 2

    def json(self):
        dict = self.__dict__.copy()
        dict["spatial_reference"] = self.spatial_reference
        return {snake_to_pascal_case(k): v for k, v in dict.items()}


@dataclass
class Interval:
    """Interval for Settings in request body.

    Parameters
    ----------
    type : str
        The interval, either "Days", "Hours", "Minutes"
    value: int
        Increment of the interval

    Example
    -------

    Interval(type="Hours", value=2)

    Is an interval of 2 hours.

    """

    type: INTERVAL_TYPES
    value: int

    def __post_init__(self):
        self.validate()

    def validate(self):
        if self.type not in INTERVAL_TYPES.__args__:
            raise ValueError(
                f"{self.type} not a valid interval-type: {INTERVAL_TYPES.__args__}"
            )

    def json(self):
        self.validate()
        return {snake_to_pascal_case(k): v for k, v in self.__dict__.items()}


@dataclass
class ReaderSettings:
    """WIWB reader-settings

    Parameters
    ----------
    start_date: datetime.date
        Reader start_date
    end_date: datetime.date
        Reader end_date
    variable_codes: List[str]
        List of WIWB variable codes
    interval: Interval
        time-interval for reader
    extent: Extend
        extent for reader
    """

    start_date: date
    end_date: date
    variable_codes: list
    interval: Union[Interval, None] = None
    extent: Union[Extent, None] = field(default_factory=Extent)

    def json(self):
        dict = self.__dict__.copy()
        dict["start_date"] = dict["start_date"].strftime("%Y%m%d%H%M%S")
        dict["end_date"] = dict["end_date"].strftime("%Y%m%d%H%M%S")
        for k in ["interval", "extent"]:
            if dict[k] is None:
                dict.pop(k)
            else:
                dict[k] = dict[k].json()

        return {snake_to_pascal_case(k): v for k, v in dict.items() if v is not None}


@dataclass
class Reader:
    """WIWB reader

    Parameters
    ----------
    data_source_code: str
        WIWB datasourcecode to read
    settings: Settings
        WIWB reader settings
    """

    data_source_code: str
    settings: Union[ReaderSettings, None] = field(default_factory=ReaderSettings)

    def json(self):
        dict = self.__dict__.copy()
        dict["settings"] = dict["settings"].json()

        return {snake_to_pascal_case(k): v for k, v in dict.items()}


@dataclass
class ExporterSettings:
    """WIWB export settings

    Parameters
    ----------
    export_projection_file: bool, optional
        To write a projection file (in case of ASCII Grid). Default is False

    """

    export_projection_file = False


@dataclass
class Exporter:
    f"""WIWB exporter

    Parameters
    ----------
    data_format_code: {DATA_FORMAT_CODES}, optional
        data-format code to export data to. Defaults to geotiff
    settings: ExporterSettings
        WIWB exporter settings

    """

    data_format_code: DATA_FORMAT_CODES = "geotiff"
    settings: Union[ExporterSettings, None] = None

    def __post_init__(self):
        self.validate()

    def validate(self):
        if self.data_format_code not in DATA_FORMAT_CODES.__args__:
            raise ValueError(
                f"{self.data_format_code} not a valid data-format-code: {DATA_FORMAT_CODES.__args__}"
            )

    def json(self):
        self.validate()
        return {
            snake_to_pascal_case(k): v
            for k, v in self.__dict__.items()
            if v is not None
        }


@dataclass
class RequestBody:
    """GetGrids request Body"""

    readers: List[Reader]
    exporter: Exporter

    def json(self):
        dict = self.__dict__.copy()
        dict["readers"] = [i.json() for i in dict["readers"]]
        dict["exporter"] = dict["exporter"].json()
        return {snake_to_pascal_case(k): v for k, v in dict.items()}


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
    geometries: InitVar[
        GeoSeries | Iterable[Union[Point, Polygon, MultiPolygon]] | None
    ] = None
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
            self.start_date,
            self.end_date,
            [self.variable_code],
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
        geometries: Optional[GeoSeries | Iterable[Union[Point, Polygon, MultiPolygon]]],
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
        geometries: Optional[GeoSeries | Iterable[Union[Point, Polygon, MultiPolygon]]],
    ) -> None:
        """Set a list or GeoSeries with Point, Polygon or MultiPolygon values. Handles conversion to
        GeoSeries and reprojection

        Parameters
        ----------
        geometries : GeoSeries | Iterable[Union[Point, Polygon, MultiPolygon]]
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

    def sample(self, stats: str | List[str] = "mean") -> DataFrame:
        """Sample statistics per geometry

        Parameters
        ----------
        stats : str | List[str]
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
