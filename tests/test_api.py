import os

CLIENT_ID = os.getenv("wiwb_client_id")


def test_authorization(auth):
    assert auth.client_id == CLIENT_ID


def test_wiwb_api(api):
    assert api.auth.client_id == CLIENT_ID
