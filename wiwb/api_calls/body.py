import logging
import tempfile
from dataclasses import InitVar, dataclass, field
from datetime import date,datetime
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
        The interval, either "Days", "Hours", "Minutes", "None"
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
        Optional Reader start_date
    end_date: datetime.date
        Optional Reader end_date
    model_run: datetime
        Optional datetime for model_run. Defaults to Last
    variable_codes: List[str]
        List of WIWB variable codes
    model_date: datetime.date
        Reader end_date
    structure_type: str
        Optional StructureType for reader
    location_codes: List[str]
        Optional list of location-codes to retrieve data for
    interval: Interval
        Optional time-interval for reader
    extent: Extend
        Optional extent for reader
    """

    variable_codes: list
    start_date: Union[date | None] = None
    end_date: Union[date | None] = None
    model_run: Union[datetime | None | str] = None
    location_codes: Union[list | None] = None
    model_date: Union[date | None] = None
    interval: Union[Interval, None] = None
    extent: Union[Extent, None] = None
    structure_type: Union[str, None] = None
    
    def json(self):
        dict = self.__dict__.copy()
        for k,v in dict.items():
            if isinstance(v, datetime) or isinstance(v, date):
                dict[k] = v.strftime("%Y%m%d%H%M%S")
            elif hasattr(dict[k], "json"):
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
    digits_to_round: int, optional
        To round digits to decimals

    """

    export_projection_file: Union[bool, None] = False
    digits_to_round: Union[int, None] = None


    def json(self):
        return {
            snake_to_pascal_case(k): v
            for k, v in self.__dict__.items()
            if v is not None
        }


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
        dict = self.__dict__.copy()
        for k,v in dict.items():
            if hasattr(dict[k], "json"):
                dict[k] = dict[k].json()

        return {snake_to_pascal_case(k): v for k, v in dict.items() if v is not None}


@dataclass
class RequestBody:
    """GetGrids request Body"""

    readers: List[Reader]
    exporter: Union[Exporter, None] = None

    def json(self):
        dict = self.__dict__.copy()
        dict["readers"] = [i.json() for i in dict["readers"]]
        if dict["exporter"] is None:
            dict.pop("exporter")
        else:
            dict["exporter"] = dict["exporter"].json()
        return {snake_to_pascal_case(k): v for k, v in dict.items()}