"""
Example tests that show all the features of pytest_nhsd_apim.

These tests actually work!
"""

import json
import pytest
import requests

from uuid import uuid4

from pytest_nhsd_apim.identity_service import (
    ClientCredentialsConfig,
    ClientCredentialsAuthenticator,
    AuthorizationCodeConfig,
    AuthorizationCodeAuthenticator,
    KeycloakUserConfig,
    KeycloakUserAuthenticator,
    TokenExchangeConfig,
    TokenExchangeAuthenticator,
)


def test_ping_endpoint(nhsd_apim_proxy_url):
    """
    Send a request to an open access endpoint.
    """

    # The nhsd_apim_proxy_url will return the URL of the proxy under test.
    # The ping endpoint should have no authentication on it.

    resp = requests.get(nhsd_apim_proxy_url + "/_ping")
    assert resp.status_code == 200
    ping_data = json.loads(resp.text)
    assert "version" in ping_data


def test_status_endpoint(nhsd_apim_proxy_url, status_endpoint_auth_headers):
    """
    Send a request to the _status endpoint, protected by a platform-wide.
    """
    # The status_endpoint_auth_headers fixture returns a dict like
    # {"apikey": "thesecretvalue"} Use it to access your proxy's
    # _status endpoint.

    resp = requests.get(nhsd_apim_proxy_url + "/_status", headers=status_endpoint_auth_headers)
    status_json = resp.json()
    assert resp.status_code == 200
    assert status_json["status"] == "pass"


# Use the pytest.mark.nhsd_apim_authorization fixture automate the
# hassle of getting valid access tokens and/or API keys to access your
# API.
@pytest.mark.nhsd_apim_authorization({"access": "application", "level": "level0"})
def test_app_level0_access(nhsd_apim_proxy_url, nhsd_apim_auth_headers):
    """
    Test you have correctly configured an endpoint for application-level0 access.
    """
    print(nhsd_apim_auth_headers)
    resp = requests.get(nhsd_apim_proxy_url + "/test-auth/app/level0")
    assert resp.status_code == 401  # unauthorized

    resp = requests.get(nhsd_apim_proxy_url + "/test-auth/app/level0", headers=nhsd_apim_auth_headers)
    assert resp.status_code == 200  # authorized


# You can provide arguments as a dict (as above) or keyword-args.
# With these arguments, you get a public/private key pair, the public
# key is "hosted" on our mock-jwks proxy, and the
# nhsd_apim_auth_headers fixture does the signed JWT flow for you.
@pytest.mark.nhsd_apim_authorization(access="application", level="level3")
def test_app_level3_access(nhsd_apim_proxy_url, nhsd_apim_auth_headers):
    """
    Test you have correctly configured an endpoint for application-level3 access.
    """
    resp = requests.get(nhsd_apim_proxy_url + "/test-auth/app/level3")
    assert resp.status_code == 401  # unauthorized

    resp = requests.get(nhsd_apim_proxy_url + "/test-auth/app/level3", headers=nhsd_apim_auth_headers)
    assert resp.status_code == 200  # authorized


# All the flavours of access tokens you can request via this pytest
# extension are cached internally. This makes running your tests as
# fast as possible. In this example you are actually using the same
# access token as the one you obtained in the previous test!
@pytest.mark.parametrize(("count"), [1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
@pytest.mark.nhsd_apim_authorization({"access": "application", "level": "level3"})
def test_app_level3_access_repeatedly(count, nhsd_apim_auth_headers):
    def th(i):
        if i == 1:
            return "st"
        if i == 2:
            return "nd"
        if i == 3:
            return "rd"
        return "th"

    print(f"This is the {count}{th(count)} test using the same credentials - {nhsd_apim_auth_headers}")


# If for any reason you want to override the caching
# the force_new_token flag can be added
@pytest.mark.parametrize(("count"), [1, 2, 3])
@pytest.mark.nhsd_apim_authorization({"access": "application", "level": "level3", "force_new_token": True})
def test_app_level3_with_force_new_token(count, nhsd_apim_auth_headers):
    def th(i):
        if i == 1:
            return "st"
        if i == 2:
            return "nd"
        if i == 3:
            return "rd"
        return "th"

    print(f"This is the {count}{th(count)} test using different credentials - {nhsd_apim_auth_headers}")


# You can include marks in a pytest parametrization to reduce
# boiler plate. This simple example matches authorization headers to
# paths and status codes. Once again, access tokens are cached for as
# long as they are valid so there are no unnecessary calls to the
# oauth server.
@pytest.mark.parametrize(
    ("expected_status_code", "test_path"),
    [
        pytest.param(
            200,
            "/test-auth/nhs-login/P0",
            marks=pytest.mark.nhsd_apim_authorization(
                access="patient",
                level="P0",
                login_form={"username": "9912003073"},
            ),
        ),
        pytest.param(
            403,
            "/test-auth/nhs-login/P5",
            marks=pytest.mark.nhsd_apim_authorization(
                access="patient",
                level="P0",
                login_form={"username": "9912003073"},
            ),
        ),
        pytest.param(
            403,
            "/test-auth/nhs-login/P9",
            marks=pytest.mark.nhsd_apim_authorization(
                access="patient",
                level="P0",
                login_form={"username": "9912003073"},
            ),
        ),
        pytest.param(
            200,
            "/test-auth/nhs-login/P5",
            marks=pytest.mark.nhsd_apim_authorization(
                access="patient",
                level="P5",
                login_form={"username": "9912003072"},
            ),
        ),
        pytest.param(
            403,
            "/test-auth/nhs-login/P9",
            marks=pytest.mark.nhsd_apim_authorization(
                access="patient",
                level="P5",
                login_form={"username": "9912003072"},
            ),
        ),
        pytest.param(
            200,
            "/test-auth/nhs-login/P9",
            marks=pytest.mark.nhsd_apim_authorization(
                access="patient",
                level="P9",
                login_form={"username": "9912003071"},
            ),
        ),
    ],
)
def test_patient_access_level_with_parametrization(
    nhsd_apim_proxy_url, expected_status_code, test_path, nhsd_apim_auth_headers
):
    """
    This parametrized test allows us to quickly check that each path
    gives us an expected status code depending on the details of how
    we authenticated to get our access token.
    """
    resp = requests.get(nhsd_apim_proxy_url + test_path, headers=nhsd_apim_auth_headers)
    assert resp.status_code == expected_status_code


# We are on our second generation of mock identity provider for
# healthcare_worker access (CIS2). This allows you to log-in using a
# username.
MOCK_CIS2_USERNAMES = {
    "aal1": ["656005750110"],
    "aal2": ["656005750109", "656005750111", "656005750112"],
    "aal3": ["656005750104", "656005750105", "656005750106"],
}


# Create a list of pytest.param for each combination of username and level for combined auth
combined_auth_params = [
    pytest.param(
        username,
        level,
        marks=pytest.mark.nhsd_apim_authorization(
            access="healthcare_worker",
            level=level,
            login_form={"username": username},
        ),
    )
    for level, usernames in MOCK_CIS2_USERNAMES.items()
    for username in usernames
]


@pytest.mark.parametrize("username, level", combined_auth_params)
def test_healthcare_worker_user_restricted_combined_auth(nhsd_apim_proxy_url, nhsd_apim_auth_headers, username, level):
    url = f"{nhsd_apim_proxy_url}/test-auth/nhs-cis2/{level}"
    resp0 = requests.get(url)
    assert resp0.status_code == 401
    resp1 = requests.get(url, headers=nhsd_apim_auth_headers)
    assert resp1.status_code == 200


# Second generation auth also allows us to simulate separate authentication and
# authorization, also called "token exchange". In this flow, we authenticate
# directly with our Mock CIS2 instance, get an ID token, and exchange it via a
# call to our oauth server for an NHSD APIM access token. From out here, it
# doesn't look too different. "combined" authentication is the default for this
# library. To use separate authentication instead, add authentication="separate"
# to the nhsd_apim_authorization mark.

# Create a combined list for separate authentication testing
separate_auth_params = [
    pytest.param(
        username,
        level,
        marks=pytest.mark.nhsd_apim_authorization(
            access="healthcare_worker",
            level=level,
            login_form={"username": username},
            authentication="separate",
        ),
    )
    for level, usernames in MOCK_CIS2_USERNAMES.items()
    for username in usernames
]


@pytest.mark.parametrize("username, level", separate_auth_params)
def test_healthcare_work_user_restricted_separate_auth(nhsd_apim_proxy_url, nhsd_apim_auth_headers, username, level):
    aal_url = f"{nhsd_apim_proxy_url}/test-auth/nhs-cis2/{level}"
    resp0 = requests.get(aal_url)
    assert resp0.status_code == 401
    resp1 = requests.get(aal_url, headers=nhsd_apim_auth_headers)
    assert resp1.status_code == 200


# we can also authenticate directly with our Mock NHS-Login instance, get an ID
# token, and exchange it via a call to our oauth server for an NHSD APIM access
# token. To use separate authentication instead, add authentication="separate"
# to the nhsd_apim_authorization mark.
@pytest.mark.nhsd_apim_authorization(
    {
        "access": "patient",
        "level": "P9",
        "login_form": {"username": "9912003071"},
        "authentication": "separate",
    }
)
def test_patient_user_restricted_separate_auth(nhsd_apim_proxy_url, nhsd_apim_auth_headers):
    P9_url = f"{nhsd_apim_proxy_url}/test-auth/nhs-login/P9"
    resp0 = requests.get(P9_url)
    assert resp0.status_code == 401
    resp1 = requests.get(P9_url, headers=nhsd_apim_auth_headers)
    assert resp1.status_code == 200


# You can test unauthenticated access with an empty
# nhsd_apim_authorization marker.  This allows you to parameterize
# unauthenicated access tests in the same way as authenticated API calls.
@pytest.mark.nhsd_apim_authorization()
def test_no_authorization_explicitly_marked(nhsd_apim_proxy_url, nhsd_apim_auth_headers):
    assert nhsd_apim_auth_headers == {}


# You can also do it without marking, though this raises a warning.
def test_no_authorization_with_not_explicitly_marked(nhsd_apim_proxy_url, nhsd_apim_auth_headers):
    assert nhsd_apim_auth_headers == {}


# You can also use the authenticators directly in case you want to run the tests
# using a specific app already available in Apigee, leaving all the marker magic
# behind this is how you can implement the diferent authenticators
def test_client_credentials_authenticator(_test_app_credentials, _jwt_keys, apigee_environment):
    # 1. Set your app config
    config = ClientCredentialsConfig(
        environment=apigee_environment,
        identity_service_base_url=f"https://{apigee_environment}.api.service.nhs.uk/oauth2-mock",
        client_id=_test_app_credentials["consumerKey"],
        jwt_private_key=_jwt_keys["private_key_pem"],
        jwt_kid="test-1",
    )

    # 2. Pass the config to the Authenticator
    authenticator = ClientCredentialsAuthenticator(config=config)

    # 3. Get your token
    token_response = authenticator.get_token()
    assert "access_token" in token_response
    token = token_response["access_token"]

    # 4. Use the token and confirm is valid
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(
        f"https://{apigee_environment}.api.service.nhs.uk/mock-jwks/test-auth/app/level3",
        headers=headers,
    )
    assert resp.status_code == 200


def test_authorization_code_authenticator(_test_app_credentials, apigee_environment):
    # 1. Set your app config
    config = AuthorizationCodeConfig(
        environment=apigee_environment,
        identity_service_base_url=f"https://{apigee_environment}.api.service.nhs.uk/oauth2-mock",
        callback_url="https://google.com/callback",
        client_id=_test_app_credentials["consumerKey"],
        client_secret=_test_app_credentials["consumerSecret"],
        scope="nhs-cis2",
        login_form={"username": "656005750104"},
    )

    # 2. Pass the config to the Authenticator
    authenticator = AuthorizationCodeAuthenticator(config=config)

    # 3. Get your token
    token_response = authenticator.get_token()
    assert "access_token" in token_response
    token = token_response["access_token"]

    # 4. Use the token and confirm is valid
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(
        f"https://{apigee_environment}.api.service.nhs.uk/mock-jwks/test-auth/nhs-cis2/aal3",
        headers=headers,
    )
    assert resp.status_code == 200


def test_token_exchange_authenticator(
    _test_app_credentials, apigee_environment, _jwt_keys, _keycloak_client_credentials
):
    # This one is a bit more interesting since we first need to get a token from
    # keycloak (our mock version of the NHS-Login provider) grab the id_token
    # from that token and then make a call to the identity service to "exchange"
    # the id_token for an Apigee access token.

    # 1. Set yout keycloack config
    config1 = KeycloakUserConfig(
        realm=f"NHS-Login-mock-{apigee_environment}",
        client_id=_keycloak_client_credentials["nhs-login"]["client_id"],
        client_secret=_keycloak_client_credentials["nhs-login"]["client_secret"],
        login_form={"username": "9912003071"},
    )

    # 2. Pass the config to the Authenticator
    authenticator = KeycloakUserAuthenticator(config=config1)

    # 3. Get your id_token
    id_token = authenticator.get_token()["id_token"]

    # 4. Set yout token exchange config
    config = TokenExchangeConfig(
        environment=apigee_environment,
        identity_service_base_url=f"https://{apigee_environment}.api.service.nhs.uk/oauth2-mock",
        client_id=_test_app_credentials["consumerKey"],
        jwt_private_key=_jwt_keys["private_key_pem"],
        jwt_kid="test-1",
        id_token=id_token,
    )

    # 5. Pass the config to the Authenticator
    authenticator = TokenExchangeAuthenticator(config=config)

    # 6. Get your token
    token_response = authenticator.get_token()
    assert "access_token" in token_response
    token = token_response["access_token"]

    # 7. Use the token and confirm is valid
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(
        f"https://{apigee_environment}.api.service.nhs.uk/mock-jwks/test-auth/nhs-login/P9",
        headers=headers,
    )
    assert resp.status_code == 200


@pytest.mark.nhsd_apim_authorization(access="application", level="level3")
def test_trace(nhsd_apim_proxy_url, nhsd_apim_auth_headers, trace):
    session_name = str(uuid4())
    header_filters = {"trace_id": session_name}
    trace.post_debugsession(session=session_name, header_filters=header_filters)

    resp = requests.get(
        nhsd_apim_proxy_url + "/test-auth/app/level3",
        headers={**header_filters, **nhsd_apim_auth_headers},
    )
    assert resp.status_code == 200

    trace_ids = trace.get_transaction_data(session_name=session_name)

    trace_data = trace.get_transaction_data_by_id(session_name=session_name, transaction_id=trace_ids[0])
    status_code_from_trace = trace.get_apigee_variable_from_trace(name="message.status.code", data=trace_data)

    trace.delete_debugsession_by_name(session_name)

    assert status_code_from_trace == "200"
