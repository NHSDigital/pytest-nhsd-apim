from typing import Literal, Dict, Optional
import json
import base64
from urllib.parse import urlparse, parse_qs
from time import time
import uuid
from functools import lru_cache, wraps

import pytest
import requests
from lxml import html
import jwt  # https://github.com/jpadilla/pyjwt
from authlib.jose import jwk
from Crypto.PublicKey import RSA

from .log import log, log_method
from .token_cache import cache_tokens


@log_method
def _session():
    """
    TLDR: We MUST clear cookies between keycloak logins.

    One of keycloak's features is that it gives a session cookie when
    we GET the login page.  It needs that session cookie when we
    submit the login form.  And it uses that same session cookie as
    our keycloak authentication.

    This is an issue if we use the same requests.Session object
    (without clearing cookies) to try and authenticate multiple users.
    After the first log in we remain logged in between tests.
    """
    # The whole purpose of this function is to draw people's attention
    # to ^this docstring^, not to save you a few keystrokes.
    return requests.session()


@log_method
@cache_tokens
def get_access_token_from_mock_cis2(
    client_id: str,
    client_secret: str,
    redirect_uri: str,
    login_form: Dict[str, str],
):
    """
    This is the first step is User Restricted Separate Auth a.k.a
    Token Exchange.  We get a set of tokens from our mock version of
    CIS2.  The reponse includes an ID token, which we will then pass
    to identity service.  Identity service validates the ID *token*,
    and *exchanges* is it for an access token for the NHSD APIM
    proxies (which probably includes the proxy under test).
    """

    # At the moment some Mock-CIS2 things are hard-coded.  But not too
    # many! It should be simple to extend it to do Mock-NHSLogin.
    login_session = _session()
    oauth_server_url = "https://identity.ptl.api.platform.nhs.uk/auth/realms/cis2-mock/protocol/openid-connect"
    resp = login_session.get(
        oauth_server_url + "/auth",
        params={
            "response_type": "code",
            "client_id": client_id,
            "scope": "openid",
            "redirect_uri": redirect_uri,
        },
    )
    log.debug(resp.text)
    tree = html.fromstring(resp.text)
    form = tree.get_element_by_id("kc-form-login")
    resp2 = login_session.post(form.action, data=login_form)
    log.debug("*"*100)
    log.debug(resp2.content)
    log.debug("*"*100)
    
    location = urlparse(resp2.history[-1].headers["location"])
    params = parse_qs(location.query)
    code = params["code"]
    resp3 = login_session.post(
        oauth_server_url + "/token",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
        },
    )
    return resp3.json()


@log_method
@cache_tokens
def get_access_token_via_user_restricted_flow_separate_auth(
    identity_service_base_url,
    keycloak_client_credentials,
    login_form,
    apigee_client_id,
    jwt_private_key,
    jwt_kid,
):
    """
    Gets an ID token from an identity provider, which would be CIS2
    (healthcare_worker) or NHSLogin (patient), in production
    environments, but for this test suite is our `ptl` keycloak
    instance.

    It then passes that ID token to identity-service, which validates
    the token, and gives us an NHSD APIM access token in return.
    """

    # This is keycloak but for real token exchange, would be CIS2 or NHSLogin.
    identity_provider_token_data = get_access_token_from_mock_cis2(
        keycloak_client_credentials["cis2"]["client_id"],
        keycloak_client_credentials["cis2"]["client_secret"],
        keycloak_client_credentials["cis2"]["redirect_uri"],
        login_form,
    )

    token_data = get_access_token_via_signed_jwt_flow(
        identity_service_base_url,
        apigee_client_id,
        jwt_private_key,
        jwt_kid,
        id_token=identity_provider_token_data["id_token"],
    )
    return token_data


@log_method
@cache_tokens
def get_access_token_via_user_restricted_flow_combined_auth(
    identity_service_base_url: str,
    client_id: str,
    client_secret: str,
    callback_url: str,
    auth_scope: Literal["nhs-login", "nhs-cis2"],
    login_form: Dict[str, str],
):
    """
    Complete the user-restricted authorization journey for CIS2 using
    our simulated_auth endpoint.

    This webpage does a pretty good job of explaining the journey:
    https://digital.nhs.uk/developer/guides-and-documentation/security-and-authorisation/user-restricted-restful-apis-nhs-cis2-combined-authentication-and-authorisation
    """
    login_session = _session()

    # 1. Hit `authorize` endpoint w/ required query params --> we
    # are redirected to the simulated_auth page. The requests package
    # follows those redirects.
    authorize_response = get_authorize_endpoint_response(
        login_session, identity_service_base_url, client_id, callback_url, auth_scope
    )
    authorize_form = get_authorization_form(authorize_response.content.decode())

    # 2. Parse simulated_auth login page.  For both generation 1
    # (simulated_auth) and generation 2 (keycloak) this presents an
    # HTML form, which must be filled in with valid data.  The tester
    # can submits their login data with the `login_form` field.
    form_submission_data = get_authorize_form_submission_data(
        authorize_form, login_form
    )

    # form_submission_data["username"] = 656005750104
    #     # And here we inject a valid mock username for keycloak.
    #     # For reference the valid mock usernames are...
    #     # 656005750104 	surekha.kommareddy@nhs.net
    #     # 656005750105 	darren.mcdrew@nhs.net
    #     # 656005750106 	riley.jones@nhs.net
    #     # 656005750107 	shirley.bryne@nhs.net
    #     form_submission_data["username"] = 656005750104

    # 3. POST the filled in form. This is equivalent to clicking the
    # "Login" button if we were a human.
    response_identity_service_login = log_in_identity_service_provider(
        login_session, authorize_response, authorize_form, form_submission_data
    )
    # 4. The simulated_auth redirected us back to the
    # identity-service, which redirected us to whatever our app's
    # callback-url was set to.  We don't actually care about the
    # content our callback-url page, we just need the auth_code that
    # was provided in the redirect.
    auth_code = get_auth_code_from_simulated_auth(response_identity_service_login)

    # 5. Finally, get an access token.
    resp = login_session.post(
        f"{identity_service_base_url}/token",
        data={
            "grant_type": "authorization_code",
            "code": auth_code,
            "redirect_uri": callback_url,
            "client_id": client_id,
            "client_secret": client_secret,
        },
    )
    resp.raise_for_status()

    # 6. Profit
    return resp.json()


@log_method
@cache_tokens
def get_access_token_via_signed_jwt_flow(
    identity_service_base_url: str,
    client_id: str,
    jwt_private_key: str,
    jwt_kid: str,
    id_token: Optional[str] = None,
):
    """
    This pattern is explained here.
    https://digital.nhs.uk/developer/guides-and-documentation/security-and-authorisation/application-restricted-restful-apis-signed-jwt-authentication

    Actually getting an access token is pretty simple as the "hard
    stuff" has already been done, getting a key-pair and attaching the
    public-key URL to our application.

    We just sign a request to the token endpoint with our private key,
    the authorization server gets the public key (from the URL we gave
    when we created the application) and verifies the private key
    corresponding to our public key signed the request.  Then it gives
    us a token.

    For application restricted access no `extra_data` is needed.
    """
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

    # Then we are doing token exchange, which requires a different grant_type
    if id_token:
        data = {
            "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
            "subject_token_type": "urn:ietf:params:oauth:token-type:id_token",
            "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
            "subject_token": id_token,
            "client_assertion": client_assertion,
        }
    else:
        data = {
            "grant_type": "client_credentials",
            "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
            "client_assertion": client_assertion,
        }

    resp = requests.post(
        url,
        data=data,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"{resp.status_code}: {resp.text}")
    return resp.json()


@lru_cache(maxsize=None)
@log_method
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
@log_method
def jwt_public_key_id(nhsd_apim_config):
    return nhsd_apim_config["JWT_PUBLIC_KEY_ID"]


@pytest.fixture(scope="session")
@log_method
def _jwt_keys(jwt_public_key_id):
    return create_jwt_key_pair(jwt_public_key_id)


@pytest.fixture(scope="session")
@log_method
def jwt_private_key_pem(_jwt_keys):
    return _jwt_keys["private_key_pem"]


@pytest.fixture(scope="session")
@log_method
def jwt_public_key_pem(_jwt_keys):
    return _jwt_keys["public_key_pem"]


@pytest.fixture(scope="session")
@log_method
def jwt_public_key(_jwt_keys):
    """
    The JWT public key in JSON Web Key format.
    """
    return _jwt_keys["json_web_key"]


@pytest.fixture(scope="session")
@log_method
def jwt_public_key_url(jwt_public_key):
    jwt_public_key_string = json.dumps(jwt_public_key)
    encoded_public_key_bytes = base64.urlsafe_b64encode(jwt_public_key_string.encode())
    return f"https://internal-dev.api.service.nhs.uk/mock-jwks/{encoded_public_key_bytes.decode()}"


@log_method
def get_authorize_endpoint_response(
    session: requests.Session,
    identity_service_base_url,
    client_id,
    callback_url,
    auth_scope: Literal["nhs-login", "nhs-cis2"],
):
    authorize_url = f"{identity_service_base_url}/authorize"
    resp = session.get(
        authorize_url,
        params={
            "client_id": client_id,
            "redirect_uri": callback_url,
            "response_type": "code",
            "scope": auth_scope,
            "state": "1234567890",
        },
    )
    if resp.status_code != 200:
        raise RuntimeError(
            f"{authorize_url} request returned {resp.status_code}: {resp.text}"
        )
    return resp


@log_method
def get_authorize_form_submission_data(authorize_form, login_options):
    inputs = list(authorize_form.inputs)
    form_submission_data = {}
    # This loop picks up the pre-populated defaults, which is
    # sufficient for simulated auth. Defaults can be appended to with
    # the "login_options".
    for _input in inputs:
        input_data = dict(_input.items())
        name = input_data["name"]
        value = input_data["value"]
        form_submission_data[name] = value

    form_submission_data.update(login_options)
    return form_submission_data


@log_method
def get_authorization_form(html_str):
    log.debug(html_str)
    tree = html.fromstring(html_str)
    form = tree.forms[0]
    return form


@log_method
def log_in_identity_service_provider(
    session: requests.Session, authorize_response, authorize_form, form_submission_data
):
    form_submit_url = authorize_form.action or authorize_response.request.url
    resp = session.request(
        authorize_form.method,
        form_submit_url,
        data=form_submission_data,
    )
    return resp


@log_method
def get_auth_code_from_simulated_auth(response_identity_service_login):
    qs = urlparse(response_identity_service_login.history[-1].headers["Location"]).query
    auth_code = parse_qs(qs)["code"]
    if isinstance(auth_code, list):
        # in case there's multiple, this was a bug at one stage
        auth_code = auth_code[0]

    return auth_code
