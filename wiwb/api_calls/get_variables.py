import logging
from dataclasses import dataclass, field
from typing import List

import requests

from wiwb.api_calls import Request

logger = logging.getLogger(__name__)


@dataclass
class GetVariables(Request):
    """GetVariables request"""

    data_source_codes: List[str] = field(default_factory=list)
    variable_codes: List[str] = field(default_factory=list)

    @property
    def url_post_fix(self) -> str:
        return "entity/variables/get"

    @property
    def json(self) -> dict:
        return {
            "DataSourceCodes": self.data_source_codes,
            "VariableCodes": self.variable_codes,
        }

    def run(self) -> List[str]:
        response = requests.post(self.url, headers=self.auth.headers, json=self.json)

        if response.ok:  # return list of data sources
            return response.json()["Variables"]

        else:  # raise Error
            response.raise_for_status()
