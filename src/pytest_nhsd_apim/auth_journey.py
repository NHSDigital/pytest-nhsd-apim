from urllib.parse import urlparse, parse_qs

import requests
from lxml import html


SESSION = requests.session()

def get_user_restricted_access_token(
    identity_service_base_url: str,
    client_id: str,
    client_secret: str,
    callback_url: str,
):

    authorize_url = f"{identity_service_base_url}/authorize"
    resp = SESSION.get(
        authorize_url,
        params={
            "client_id": client_id,
            "redirect_uri": callback_url,
            "response_type": "code",
            "state": "1234567890",
        },
    )

    if resp.status_code != 200:
        raise RuntimeError(f"{authorize_url} request returned {resp.status_code}: {resp.text}")
    tree = html.fromstring(resp.content.decode())

    state = None
    for form in tree.body:
        assert form.tag == "form"
        input_elems = [item for item in form if item.tag == "input"]
        state = dict(input_elems[0].items())["value"]

        # TODO make this configurable
        simulated_auth_url = "https://internal-dev.api.service.nhs.uk/mock-nhsid-jwks/simulated_auth"
        resp2 = SESSION.post(
            simulated_auth_url, data={"state": state}
        )

    # We do the POST identity-service expects from the callback
    # url webpage ourselves...

    # requests has been redirected (like a browser) to whatever
    # our callback_url is.  The auth code was in the
    # redirect query string, so we go grab it from the redirect
    # history.
    qs = urlparse(resp2.history[-1].headers["Location"]).query
    auth_code = parse_qs(qs)["code"]
    if isinstance(auth_code, list):
        auth_code = auth_code[0]

    resp3 = SESSION.post(
        f"{identity_service_base_url}/token",
        data={
            "grant_type": "authorization_code",
            "code": auth_code,
            "redirect_uri": callback_url,
            "client_id": client_id,
            "client_secret": client_secret
        },
    )
    token_data = resp3.json()
    return token_data["access_token"]
