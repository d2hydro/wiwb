"""Authorization for the WIWB API"""

from dataclasses import dataclass, field

from typing import Union
from datetime import datetime, timedelta, UTC
import jwt
import requests
from wiwb.constants import AUTH_URL, CLIENT_ID, CLIENT_SECRET


@dataclass
class Auth:
    f"""Authorization class for WIWB API.

    Will provide valid headers and tokens for the WIWB API

    Attributes
    ----------
    client_id : str
        A valid client_id for the WIWB API. If not provided it will be read from the os environment
         variable `wiwb_client_id`. By default {CLIENT_ID}.
    client_secret : str
        A valid client_secret for the WIWB API. If not provided it will be read from the os environment
         variable `wiwb_client_secret`. By default {CLIENT_SECRET}.
    url: str
        A valid WIWB token url. By default {AUTH_URL}.
    token: str
        A valid WIWB access token

    Examples
    --------
    from wiwb import Auth

    >>> auth = Auth() # initalialize wiwb authorization
    >>> auth.token  # returns a valid token
    'eyJhbGciOiJS...............`

    >>> auth.headers # returns valid headers for requests to the WIWB API
    {{"content-type": "application/json", "Authorization": 'eyJhbGciOiJS...............`}}
    """
    client_id: str = CLIENT_ID
    client_secret: str = CLIENT_SECRET
    url: str = AUTH_URL
    _token: Union[str, None] = field(default=None, repr=False)

    def __post_init__(self):

        # check if client_id and client_secret are valid
        if self.client_id is None:
            raise ValueError(
                f"Invalid 'client_id': '{self.client_id}'. Provide at init or specify 'wiwb_client_id' as os environment variable"  # noqa:E501
            )

        if self.client_secret is None:
            raise ValueError(
                f"Invalid 'client_secret':  '{self.client_secret}'. Provide at init or specify 'wiwb_client_id' as os environment variable"  # noqa:E501
            )

        # get a token to get started
        self.get_token()

    @property
    def token(self) -> str:
        """Return a valid WIWB access token."""
        if not self.token_valid:
            self.get_token()
        return self._token

    @property
    def token_valid(self) -> bool:
        """Check if current token is still valid."""
        token_decoded = jwt.decode(self._token, options={"verify_signature": False})
        token_exp_datetime = datetime.fromtimestamp(token_decoded["exp"], UTC)
        # token_exp_datetime = datetime.utcfromtimestamp(token_decoded["exp"])
        current_datetime = datetime.now(UTC) - timedelta(minutes=1)
        # current_datetime = datetime.utcnow() - timedelta(minutes=1)
        return current_datetime < token_exp_datetime

    @property
    def headers(self) -> dict:
        """Headers for WIWB API requests"""
        return {
            "content-type": "application/json",
            "Authorization": "Bearer " + self.token,
        }

    def get_token(self) -> str:
        """Get, and store, a fresh WIWB access token"""
        response = requests.post(
            self.url,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "client_credentials",
            },
        )
        if response.ok:
            self._token = response.json()["access_token"]
        else:
            response.raise_for_status()
