import requests
import logging
from typing import List, Dict
from wiwb.api_calls import Request
from dataclasses import dataclass, field


logger = logging.getLogger(__name__)

PRIMARY_STRUCTURE_TYPES = [
    "EnsembleGrid",
    "EnsembleTimeSeries",
    "Event",
    "Grid",
    "ModelGrid",
    "ModelTimeSeries",
    "TimeSeries",
]


@dataclass
class GetDataSources(Request):
    # FIXME: let's go for Python >= 3.8 and use typing.Literal
    primary_structure_types: List[str] = field(default_factory=lambda: ["Grid"])

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
