"""
Example tests that show all the features of pytest_nhsd_apim.

These tests actually work!
"""
import json
import pytest
import requests

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

    resp = requests.get(
        nhsd_apim_proxy_url + "/_status", headers=status_endpoint_auth_headers
    )
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
    resp = requests.get(nhsd_apim_proxy_url + "/test-auth/app/level0")
    assert resp.status_code == 401  # unauthorized

    resp = requests.get(
        nhsd_apim_proxy_url + "/test-auth/app/level0", headers=nhsd_apim_auth_headers
    )
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

    resp = requests.get(
        nhsd_apim_proxy_url + "/test-auth/app/level3", headers=nhsd_apim_auth_headers
    )
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

    print(
        f"This is the {count}{th(count)} test using the same credentials - {nhsd_apim_auth_headers}"
    )


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
                login_form={"auth_method": "P0"},
            ),
        ),
        pytest.param(
            403,
            "/test-auth/nhs-login/P5",
            marks=pytest.mark.nhsd_apim_authorization(
                access="patient",
                level="P0",
                login_form={"auth_method": "P0"},
            ),
        ),
        pytest.param(
            403,
            "/test-auth/nhs-login/P9",
            marks=pytest.mark.nhsd_apim_authorization(
                access="patient",
                level="P0",
                login_form={"auth_method": "P0"},
            ),
        ),
        pytest.param(
            200,
            "/test-auth/nhs-login/P5",
            marks=pytest.mark.nhsd_apim_authorization(
                access="patient",
                level="P5",
                login_form={"auth_method": "P5"},
            ),
        ),
        pytest.param(
            403,
            "/test-auth/nhs-login/P9",
            marks=pytest.mark.nhsd_apim_authorization(
                access="patient",
                level="P5",
                login_form={"auth_method": "P5"},
            ),
        ),
        pytest.param(
            200,
            "/test-auth/nhs-login/P9",
            marks=pytest.mark.nhsd_apim_authorization(
                access="patient",
                level="P9",
                login_form={"auth_method": "P9"},
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
MOCK_CIS2_USERNAMES = ["656005750104", "656005750105", "656005750106", "656005750107"]

# You can make the parametrization less verbose by using a function to
# construct each pytest.param!
def cis2_aal3_mark(username: str):
    return pytest.param(
        marks=pytest.mark.nhsd_apim_authorization(
            access="healthcare_worker",
            level="aal3",
            login_form={"username": username},
        ),
    )


# It's getting pretty abstract now, but we're accessing the same
# endpoint using access tokens granted to four different mock
# users. Each is a valid mock user with aal3 credentials and so is
# granted a token we can use.
@pytest.mark.parametrize(
    (),
    [cis2_aal3_mark(username) for username in MOCK_CIS2_USERNAMES],
)
def test_healthcare_worker_user_restricted_combined_auth(
    nhsd_apim_proxy_url, nhsd_apim_auth_headers
):
    resp0 = requests.get(nhsd_apim_proxy_url + "/test-auth/nhs-cis2/aal3")
    assert resp0.status_code == 401
    resp1 = requests.get(
        nhsd_apim_proxy_url + "/test-auth/nhs-cis2/aal3", headers=nhsd_apim_auth_headers
    )
    assert resp1.status_code == 200


# Second generation auth also allows us to simulate separate
# authentication and authorization, also called "token exchange". In
# this flow, we authenticate directly with our Mock CIS2 instance, get
# an ID token, and exchange it via a call to our oauth server for an
# NHSD APIM access token. From out here, it doesn't look too
# different. "combined" authentication is the default for this
# library. To use separate authentication instead, add
# authentication="separate" to the nhsd_apim_authorization mark.
@pytest.mark.nhsd_apim_authorization(
    {
        "access": "healthcare_worker",
        "level": "aal3",
        "login_form": {"username": "aal3"},
        "authentication": "separate",
    }
)
def test_healthcare_work_user_restricted_separate_auth(
    nhsd_apim_proxy_url, nhsd_apim_auth_headers
):
    aal3_url = f"{nhsd_apim_proxy_url}/test-auth/nhs-cis2/aal3"
    resp0 = requests.get(aal3_url)
    assert resp0.status_code == 401
    resp1 = requests.get(aal3_url, headers=nhsd_apim_auth_headers)
    assert resp1.status_code == 200
