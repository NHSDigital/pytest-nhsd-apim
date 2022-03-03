import json
import base64
import logging
from typing import Optional, Dict
from urllib.parse import urlparse, parse_qs
from time import time
import uuid
from functools import lru_cache

import pytest
import requests
from lxml import html
import jwt  # https://github.com/jpadilla/pyjwt
from authlib.jose import jwk
from Crypto.PublicKey import RSA

LOG = logging.getLogger(__name__)

_SESSION = requests.session()
_CACHED_CIS2_SIMULATED_AUTH_TOKEN_DATA = {}
_CACHED_JWT_TOKEN_DATA = {}


def _insert_into_cache(client_id,
                       cache: Dict,
                       token):
    if "issued_at" not in token:
        # only present on app-restricted tokens.
        # we can inject this ourselves
        token["issued_at"] = time() - 5000  # assume 5 seconds ago, probably was more recently
    cache[client_id] = token


def _check_cache(
    client_id: str,
    cache: Dict,
    grace_period_seconds: int = 10
) -> Optional[str]:
    """
    Return a non-expired access token with the same client_id or None.
    """
    if client_id not in cache:
        return None

    old_token = cache[client_id]
    now_ish = int(time()) + grace_period_seconds
    LOG.debug(f"old_token_is: {old_token}")
    # issued at epoch_time in milliseconds, expires_in is in seconds, so need factor of 1000
    if now_ish < int(old_token["issued_at"]) + 1000*int(old_token["expires_in"]):
        return old_token["access_token"]


def get_access_token_via_user_restricted_flow(identity_service_base_url: str,
                                              client_id: str,
                                              client_secret: str,
                                              callback_url: str,
                                              auth_scope: str,
                                              permission_lvl: str):
    """
    Complete the user-restricted authorization journey for CIS2 using
    our simulated_auth endpoint.

    This webpage does a pretty good job of explaining the journey:
    https://digital.nhs.uk/developer/guides-and-documentation/security-and-authorisation/user-restricted-restful-apis-nhs-cis2-combined-authentication-and-authorisation
    """
    cache_id = f"{client_id}_{auth_scope}_{permission_lvl}"
    cached_token = _check_cache(cache_id, _CACHED_CIS2_SIMULATED_AUTH_TOKEN_DATA)
    if cached_token:
        return cached_token

    # 1. Hit `authorize` endpoint w/ required query params --> we
    # are redirected to the simulated_auth page. The requests package
    # follows those redirects.
    authorize_response = get_authorize_endpoint_response(identity_service_base_url,
                                                         client_id,
                                                         callback_url,
                                                         auth_scope)
    authorize_form = get_authorization_form(authorize_response)

    # 2. Parse simulated_auth login page. IRL you'd need to log in with
    # some credentials here, but no such hassle on the simulated_auth
    # page.
    form_submission_data = get_authorize_form_submission_data(authorize_form, permission_lvl)

    # 3. page, this is equivalent to clicking the "Login" button.
    response_identity_service_login = log_in_identity_service_provider(authorize_response,
                                                                       authorize_form,
                                                                       form_submission_data)
    # 4. The simulated_auth redirected us back to the
    # identity-service, which redirected us to whatever our app's
    # callback-url was set to.  We don't actually care about the
    # content our callback-url page, we just need the auth_code that
    # was provided in the redirect.
    auth_code = get_auth_code_from_simulated_auth(response_identity_service_login)

    # 5. Finally, get an access token.
    token_data = get_identity_service_access_token(identity_service_base_url, auth_code, callback_url,
                                                   client_id, client_secret)
    _insert_into_cache(cache_id, _CACHED_CIS2_SIMULATED_AUTH_TOKEN_DATA, token_data)

    # 6. Profit
    return token_data["access_token"]


def get_access_token_via_signed_jwt_flow(identity_service_base_url: str,
                                         client_id: str,
                                         jwt_private_key: str,
                                         jwt_kid: str):
    """
    This pattern is explained here.
    https://digital.nhs.uk/developer/guides-and-documentation/security-and-authorisation/application-restricted-restful-apis-signed-jwt-authentication

    Actually getting an access token is pretty simple as the (not too)
    "hard stuff" has already been done, getting a key-pair and
    attaching the public-key URL to our application.

    We just sign a request to the token endpoint with our private key,
    the authorization server gets the public key (from the URL we gave
    when we created the application) and verifies the private key
    corresponding to our public key signed the request.  Then it gives
    us a token.
    """

    # Check cache before requesting a new token
    cached_token = _check_cache(client_id, _CACHED_JWT_TOKEN_DATA)
    if cached_token:
        return cached_token

    url = f"{identity_service_base_url}/token"
    claims = {
        "sub": client_id,
        "iss": client_id,
        "jti": str(uuid.uuid4()),
        "aud": url,
        "exp": int(time()) + 300,  # 5 minutes in the future
    }

    additional_headers = {"kid": jwt_kid}
    client_assertion = jwt.encode(
        claims, jwt_private_key, algorithm="RS512", headers=additional_headers
    )
    resp = _SESSION.post(url,
                         data={"grant_type": "client_credentials",
                               "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
                               "client_assertion": client_assertion},
                         timeout=3)
    token_data = resp.json()
    _insert_into_cache(client_id, _CACHED_JWT_TOKEN_DATA, token_data)

    return token_data["access_token"]


@lru_cache(maxsize=None)
def create_jwt_key_pair(key_id):
    """
    Pure python instructions to generate a public-key/ private-key
    pair in the correct format.
    """
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


@pytest.fixture(scope="session")
def jwt_public_key_id(nhsd_apim_config):
    return nhsd_apim_config["JWT_PUBLIC_KEY_ID"]


@pytest.fixture(scope="session")
def _jwt_keys(jwt_public_key_id):
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


def get_authorize_endpoint_response(identity_service_base_url, client_id, callback_url, auth_scope):
    authorize_url = f"{identity_service_base_url}/authorize"
    resp = _SESSION.get(authorize_url,
                        params={"client_id": client_id,
                                "redirect_uri": callback_url,
                                "response_type": "code",
                                "scope": auth_scope,  # nhs-login, nhs-cis2
                                "state": "1234567890"},
                        timeout=3)
    if resp.status_code != 200:
        raise RuntimeError(f"{authorize_url} request returned {resp.status_code}: {resp.text}")
    return resp


def get_authorize_form_submission_data(authorize_form, permission_lvl):
    inputs = list(authorize_form.inputs)
    form_submission_data = {}

    # This loop picks up the pre-populated defaults, which is
    # sufficient for simulated auth. If we ever want to choose a
    # different one of those radio buttons... this will need a
    # rethink.
    for _input in inputs:
        input_data = dict(_input.items())
        name = input_data["name"]
        value = input_data["value"]
        form_submission_data[name] = value
        LOG.debug(f"form_inputs_is:: {name} - {value}")
        if value == permission_lvl:
            break
    LOG.debug(f"form_submission_data_is: {form_submission_data}")

    # And here we inject a valid mock username for keycloak.
    # For reference the valid mock usernames are...
    # 656005750104 	surekha.kommareddy@nhs.net
    # 656005750105 	darren.mcdrew@nhs.net
    # 656005750106 	riley.jones@nhs.net
    # 656005750107 	shirley.bryne@nhs.net
    form_submission_data["username"] = 656005750104

    return form_submission_data


def get_authorization_form(authorize_response):
    html_str = authorize_response.content.decode()
    tree = html.fromstring(html_str)
    form = tree.forms[0]
    return form


def log_in_identity_service_provider(authorize_response, authorize_form, form_submission_data):

    form_submit_url = authorize_form.action or authorize_response.request.url
    resp = _SESSION.request(authorize_form.method, form_submit_url, data=form_submission_data)
    LOG.debug(f"resp2_is: {resp.text}")

    return resp


def get_auth_code_from_simulated_auth(response_identity_service_login):
    qs = urlparse(response_identity_service_login.history[-1].headers["Location"]).query
    auth_code = parse_qs(qs)["code"]
    if isinstance(auth_code, list):
        # in case there's multiple, this was a bug at one stage
        auth_code = auth_code[0]

    return auth_code


def get_identity_service_access_token(identity_service_base_url, auth_code, callback_url, client_id, client_secret):
    resp = _SESSION.post(f"{identity_service_base_url}/token",
                         data={"grant_type": "authorization_code",
                               "code": auth_code,
                               "redirect_uri": callback_url,
                               "client_id": client_id,
                               "client_secret": client_secret},
                         timeout=3)
    token_data = resp.json()
    return token_data
