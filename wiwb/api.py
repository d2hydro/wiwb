from wiwb import Auth
from dataclasses import dataclass
from typing import Union
from wiwb import api_calls
from wiwb.globals import API_URL


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

    def get_grids(self, **kwargs):
        get_grids = api_calls.GetVariables(
            base_url=self.base_url, auth=self.auth, **kwargs
        )
        return get_grids
