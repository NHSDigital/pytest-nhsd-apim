import json
import base64
from typing import Optional
from urllib.parse import urlparse, parse_qs
import pathlib
from time import time
import uuid

import pytest
import requests
from lxml import html
import jwt  # https://github.com/jpadilla/pyjwt
from authlib.jose import jwk
from Crypto.PublicKey import RSA


from .config import nhsd_apim_config


SESSION = requests.session()
SESSION.headers = {"foo": "bar"}

def get_access_token_via_user_restricted_flow(
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



_CACHED_JWT_TOKEN_DATA = {}

def get_jwt_cached_token(client_id) -> Optional[str]:
    """
    Return a non-expired access token with the same client_id or None.
    """
    if client_id not in _CACHED_JWT_TOKEN_DATA:
        return None
    old_token = _CACHED_JWT_TOKEN_DATA[client_id]
    now_ish = int(time.time()) + 10  # Don't cut it too close
    if now_ish < old_token["issued_at"] + old_token["expires_in"]:
        return old_token["access_token"]


def get_access_token_via_signed_jwt_flow(
    identity_service_base_url: str,
    client_id: str,
    jwt_private_key: str,
    jwt_kid: str,
    use_cached_tokens=True,
):
    # Check cache before regenerating token
    if use_cached_tokens:
        token = get_jwt_cached_token(client_id)
        if token:
            return token

    url = f"{identity_service_base_url}/token"
    claims = {
        "sub": client_id,
        "iss": client_id,
        "jti": str(uuid.uuid4()),
        "aud": url,
        "exp": int(time()) + 300,  # 5mins in the future
    }

    additional_headers = {"kid": jwt_kid}
    client_assertion = jwt.encode(
        claims, jwt_private_key, algorithm="RS512", headers=additional_headers
    )
    resp = SESSION.post(
        url,
        data={
            "grant_type": "client_credentials",
            "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
            "client_assertion": client_assertion,
        },
    )
    token_data = resp.json()
    _CACHED_JWT_TOKEN_DATA[client_id] = token_data
    
    return token_data["access_token"]



def create_jwt_key_pair(key_id):
    
    key_size = 4096
    key = RSA.generate(key_size)
    private_key_pem = key.exportKey("PEM").decode()
    public_key_pem = key.publickey().exportKey("PEM").decode()

    # This is the JSON formatted public key
    json_web_key = jwk.dumps(
        public_key_pem, kty="RSA", crv_or_size=key_size, alg="RS512"
    )
    json_web_key["kid"] = key_id
    json_web_key["use"] = "sig"

    return {
        "public_key_pem": public_key_pem,
        "private_key_pem": private_key_pem,
        "json_web_key": {"keys": [json_web_key]},
    }


# @pytest.fixture(scope="session")
# def jwt_public_key_id():
#     return "test-1"
    # return nhsd_apim_config["JWT_PUBLIC_KEY_ID"]

@pytest.fixture(scope="session")
def _jwt_keys():
    jwt_public_key_id = "test-1"
    return create_jwt_key_pair(jwt_public_key_id)
    
@pytest.fixture(scope="session")
def jwt_private_key_pem(_jwt_keys):
    return _jwt_keys["private_key_pem"]
    
@pytest.fixture(scope="session")
def jwt_public_key_pem(_jwt_keys):
    return _jwt_keys["public_key_pem"]
    
@pytest.fixture(scope="session")
def jwt_public_key(_jwt_keys):
    """
    The JWT public key in JSON Web Key format.
    """
    return _jwt_keys["json_web_key"]

@pytest.fixture(scope="session")
def jwt_public_key_url(jwt_public_key):
    jwt_public_key_string = json.dumps(jwt_public_key)
    encoded_public_key_bytes = base64.urlsafe_b64encode(jwt_public_key_string.encode())
    return f"https://internal-dev.api.service.nhs.uk/mock-jwks/{encoded_public_key_bytes.decode()}"
