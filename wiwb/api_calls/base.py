from dataclasses import dataclass
from wiwb.auth import Auth


@dataclass
class Request:
    auth: Auth
    base_url: str

    def __post_init__(self):
        if self.base_url.endswith("/"):
            self.base_url = self.base_url[:-1]

    @property
    def url(self) -> str:
        return f"{self.base_url}/{self.url_post_fix}"
