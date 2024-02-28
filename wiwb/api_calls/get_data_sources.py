import requests
import logging
from typing import Dict
from wiwb.api_calls import Request
from dataclasses import dataclass, field
from wiwb.constants import PRIMARY_STRUCTURE_TYPES

logger = logging.getLogger(__name__)


@dataclass
class GetDataSources(Request):
    """GetDataSources request"""

    primary_structure_types: PRIMARY_STRUCTURE_TYPES = field(
        default_factory=lambda: ["Grid"]
    )

    @property
    def url_post_fix(self) -> str:
        return "entity/datasources/get"

    def run(self) -> Dict:
        response = requests.post(self.url, headers=self.auth.headers, json={})

        if response.ok:  # return list of data sources
            return {
                k: v
                for k, v in response.json()["DataSources"].items()
                if v["PrimaryStructureType"] in self.primary_structure_types
            }

        else:  # raise Error
            response.raise_for_status()
