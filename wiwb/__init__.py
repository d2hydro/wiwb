__version__ = "2024.4.2"
import warnings

from wiwb.api import Api
from wiwb.auth import Auth

__all__ = ["Auth", "Api"]

warnings.filterwarnings(
    "ignore",
    category=DeprecationWarning,
    module="dateutil",
    message="Use timezone-aware objects to represent datetimes in UTC",
)
warnings.filterwarnings(
    "ignore",
    category=UserWarning,
    module="pyproj",
    message="You will likely lose important projection information when converting to a PROJ string from another",
)
warnings.filterwarnings(
    "ignore",
    category=UserWarning,
    module="rasterstats",
    message="Setting nodata to -999; specify nodata explicitly",
)
