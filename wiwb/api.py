import requests
from wiwb import Auth
from dataclasses import dataclass, field
from typing import Union, List
from wiwb import api_calls

API_URL = "https://wiwb.hydronet.com/api"


@dataclass
class Api:
    """Python API for WIWB service."""

    auth: Union[Auth, None] = None
    base_url: str = API_URL

    def __post_init__(self):
        if self.auth is None:
            self.auth = Auth()
        if self.base_url is None:
            raise ValueError(
                f"Provide a valid base_url. Current value is {self.base_url}"
            )

    def get_data_sources(self, **kwargs):
        api_call = api_calls.GetDataSources(
            base_url=self.base_url, auth=self.auth, **kwargs
        )
        return api_call.run()

    def get_variables(self, **kwargs):
        api_call = api_calls.GetVariables(
            base_url=self.base_url, auth=self.auth, **kwargs
        )
        return api_call.run()
