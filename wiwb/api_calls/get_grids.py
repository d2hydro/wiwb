import logging
from wiwb.api_calls import Request
from dataclasses import dataclass, field
from typing import Iterable, List, Tuple, Union, Optional
from collections.abc import Iterable
from geopandas import GeoSeries
from shapely.geometry import Point, Polygon, MultiPolygon
from datetime import date
import pandas as pd
from wiwb.converters import snake_to_pascal_case
import pyproj
import requests
from wiwb.sample import sample_netcdf
from pathlib import Path
import tempfile
import xarray


FILE_SUFFICES = {
    "geotiff": "zip",
    "aaigrid": "hdf5",
    "hdf5": "hdf5",
    "netcdf4.cf1p6": "nc",
    "netcdf4.cf1p6.zip": "zip",
}

TIME_INTERVAL = ["Days", "Hours", "Minutes"]

DEFAULT_BOUNDS = (109950, 438940, 169430, 467600)
DEFAULT_CRS = 28992
IMPLEMENTED_GEOMETRY_TYPES = [Point, Polygon, MultiPolygon]

logger = logging.getLogger(__name__)


@dataclass
class Extent:
    """Extent for Settings in request body."""

    xll: float = DEFAULT_BOUNDS[0]
    yll: float = DEFAULT_BOUNDS[1]
    xur: float = DEFAULT_BOUNDS[2]
    yur: float = DEFAULT_BOUNDS[3]
    epsg: int = DEFAULT_CRS

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
        dict.pop("epsg")
        dict["spatial_reference"] = self.spatial_reference
        return {snake_to_pascal_case(k): v for k, v in dict.items()}


@dataclass
class Interval:
    """Interval for Settings in request body."""

    type: str
    value: int

    def json(self):
        return {snake_to_pascal_case(k): v for k, v in self.__dict__.items()}


@dataclass
class ReaderSettings:
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
    data_source_code: str
    settings: Union[ReaderSettings, None] = field(default_factory=ReaderSettings)

    def json(self):
        dict = self.__dict__.copy()
        dict["settings"] = dict["settings"].json()

        return {snake_to_pascal_case(k): v for k, v in dict.items()}


@dataclass
class ExporterSettings:
    export_projection_file = False


@dataclass
class Exporter:
    data_format_code: str = "geotiff"
    settings: Union[ExporterSettings, None] = None

    def json(self):
        return {
            snake_to_pascal_case(k): v
            for k, v in self.__dict__.items()
            if v is not None
        }


@dataclass
class RequestBody:
    readers: List[Reader]
    exporter: Exporter

    def json(self):
        dict = self.__dict__.copy()
        dict["readers"] = [i.json() for i in dict["readers"]]
        dict["exporter"] = dict["exporter"].json()
        return {snake_to_pascal_case(k): v for k, v in dict.items()}


@dataclass
class GetGrids(Request):
    data_source_code: str
    variable_code: str
    start_date: date
    end_date: date
    unzip: bool = True
    interval: Tuple[str, int] = ("Hours", 1)
    data_format_code: str = "geotiff"
    epsg: Union[int, None] = (
        DEFAULT_CRS  # epsg always before geometries so crs can be alligned
    )
    geometries: GeoSeries | Iterable[Union[Point, Polygon, MultiPolygon]] | None = (
        None  # geometries always before bounds
    )
    bounds: Union[Tuple[float, float, float, float], None] = DEFAULT_BOUNDS
    _response: Union[requests.Response, None] = None

    # handles specific preperation of properties
    def __setattr__(self, prop, val):
        if prop == "geometries":
            val = self._to_geoseries(val)
        if prop == "epsg":
            geoseries = self._reproject_geoseries(epsg=val)
            if geoseries is not None:
                self.geometries = geoseries
        if prop == "bounds":
            val = self._get_bounds(val)
        super().__setattr__(prop, val)

    def __post_init__(self):
        if self.epsg is None:
            raise ValueError(
                "epsg can not be None. Specify geometries with crs or set epsg directly"
            )

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
            extent=Extent(*self.bounds, epsg=self.epsg),
        )

        reader = Reader(self.data_source_code, settings=reader_settings)

        exporter = Exporter(data_format_code=self.data_format_code)

        return RequestBody(readers=[reader], exporter=exporter)

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
    def url_post_fix(self) -> str:
        return "grids/get"

    def _to_geoseries(
        self,
        geometries: GeoSeries | Iterable[Union[Point, Polygon, MultiPolygon]] | None,
    ):

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

    def _reproject_geoseries(
        self, geoseries: GeoSeries | None = None, epsg: int | None = None
    ):
        if geoseries is None:
            geoseries = self.geometries
        if epsg is None:
            epsg = self.epsg

        if geoseries is not None:
            ## if no epsg, but geometries, we set crs from geometries
            if (epsg is None) and (geoseries.crs is not None):
                epsg = geoseries.crs.to_epsg()
            ## if epsg, but geometries.crs, we set geometries.crs from crs
            elif (epsg is not None) and (geoseries.crs is None):
                geoseries.crs = epsg
            ## if epsg and geometries.crs we reproject geometies to epsg
            elif (epsg is not None) and (geoseries.crs is not None):
                geoseries = geoseries.to_crs(epsg)
            else:
                raise ValueError(
                    "Either specify epsg or provide geoseries with crs. Both are None"
                )

        return geoseries

    def _get_bounds(self, bounds: Union[Tuple[float, float, float, float], None]):
        if (
            self.geometries is not None
        ):  # if geometries are specified, we'll get bounds from geometries
            bounds = tuple(self.geometries.total_bounds)
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

    def write_tempfile(self):
        with tempfile.NamedTemporaryFile(
            suffix=FILE_SUFFICES[self.data_format_code], delete=False
        ) as tmp_file:
            tmp_file_path = Path(tmp_file.name)
            tmp_file.write(self._response.content)
        return tmp_file_path

    def sample(self, stats: Union[str, List[str]] = "mean"):
        if isinstance(stats, str):
            stats = [stats]

        # check if geometries are set
        if self.geometries is None:
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
            geometries=self.geometries,
            stats=stats,
            unlink=True,
        )

        return df

    def write(self, output_dir: Union[str, Path]):
        """Write response.content to an output-file"""
        if self._response is None:
            self.run()

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / self.file_name
        output_file.write_bytes(self._response.content)
