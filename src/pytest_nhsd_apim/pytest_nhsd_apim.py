from typing import Callable
import pytest
import os
import requests
from uuid import uuid4
from datetime import datetime

APIGEE_BASE_URL = "https://api.enterprise.apigee.com/v1/"


def _now_ms() -> int:
    now_s = datetime.utcnow().timestamp()
    return int(1000 * now_s)

##########
# HOOKS
##########
def pytest_addoption(parser):
    group = parser.getgroup("nhsd-apim")
    group.addoption(
        "--apigee-access-token",
        action="store",
        dest="APIGEE_ACCESS_TOKEN",
        help="Access token to log into apigee edge API, output of get_token",
    )
    group.addoption(
        "--apigee-organization",
        action="store",
        dest="APIGEE_ORGANIZATION",
        help="nhsd-nonprod/nhsd-prod",
        default="nhsd-nonprod",
    )
    group.addoption(
        "--apigee-developer",
        action="store",
        dest="APIGEE_DEVELOPER",
        help="Developer under which to register the app",
        default="apm-testing-internal-dev@nhs.net",
    )

def pytest_configure(config):
    config.addinivalue_line("markers", "products(products): Marker to indicate the list of products the test app should be subscribed to for this test.")


@pytest.fixture(scope="session")
def nhsd_apim_config(request):
    def _get_config(name):
        cmd_line_value = getattr(request.config.option, name)
        if cmd_line_value is not None:
            return cmd_line_value
        env_var_value = os.environ.get(name)
        if env_var_value is not None:
            return env_var_value
        raise ValueError(f"Required config: {name} is not set.")

    return {
        k: _get_config(k)
        for k in ["APIGEE_ACCESS_TOKEN", "APIGEE_ORGANIZATION", "APIGEE_DEVELOPER"]
    }


@pytest.fixture(scope="session")
def _apigee_edge_session(nhsd_apim_config):
    token = nhsd_apim_config["APIGEE_ACCESS_TOKEN"]
    session = requests.session()
    session.headers = {"Authorization": f"Bearer {token}"}
    return session


@pytest.fixture(scope="session")
def apigee_products(_apigee_edge_session, nhsd_apim_config):
    got_all_products = False
    org = nhsd_apim_config["APIGEE_ORGANIZATION"]
    products_url = APIGEE_BASE_URL + f"organizations/{org}/apiproducts"
    params = {"expand": "true"}
    products = []
    while not got_all_products:
        resp = _apigee_edge_session.get(products_url, params=params)
        new_products = resp.json()["apiProduct"]
        products.extend(new_products)
        if len(new_products) == 1000:
            last = products.pop()
            params.update({"startKey": last["name"]})
        else:
            got_all_products = True
    return products


@pytest.fixture(scope="session")
def _apigee_app_base_url(nhsd_apim_config):
    org = nhsd_apim_config["APIGEE_ORGANIZATION"]
    dev = nhsd_apim_config["APIGEE_DEVELOPER"]
    url = APIGEE_BASE_URL + f"organizations/{org}/developers/{dev}/apps"
    return url



@pytest.fixture(scope="session")
def _test_app(_apigee_app_base_url, _apigee_edge_session):
    """
    Create an ephemeral app that lasts the duration of the pytest
    session.

    Note that a single app can have many sets of credentials.  Each
    set of credentials can be subscribed to a unique set of products,
    so one app can test your API against multiple product
    configurations should you need to do so.  See `app_credentials`
    for details.
    """

    app = {"name": f"apim-auto-{uuid4()}"}
    create_resp = _apigee_edge_session.post(_apigee_app_base_url, json=app)
    assert create_resp.status_code == 201

    yield create_resp.json()
    delete_resp = _apigee_edge_session.delete(_apigee_app_base_url + "/" + app["name"])
    assert delete_resp.status_code == 200


@pytest.fixture()
def test_app(_test_app, _apigee_edge_session, _apigee_app_base_url) -> Callable:
    """
    A Callable that gets you the current state of the test app.
    """
    # pytest fixtures are wonderful, and do lots of magical things.

    # In any reasonably well developed pytest extension, we have a
    # complicated dependency graph of fixtures calling fixtures
    # calling fixture.  We are using some "update-state" fixtures to
    # tell apigee to update the app, a nice UX IMO. However, fixtures
    # are called at-most once per test. So if we provided the
    # "current-state" of the app as a dict from a fixture, it would be
    # hard to know if the "update-state" fixture was called
    # before/after the "current-state" fixture. Therefore we let
    # Apigee be the sole arbiter of the current state at the cost of
    # an API call.

    # In any case, if we design the higher level abstrations well,
    # most of the time this won't be needed.
    def app():
        resp = _apigee_edge_session.get(_apigee_app_base_url + "/" + _test_app["name"])
        return resp.json()
    return app


@pytest.fixture()
def test_app_credentials(request, _apigee_app_base_url, _apigee_edge_session, test_app, apigee_products):
    """
    Use this fixture to get a set of credentials which has access to a
    set of products defined via a pytest mark.  The mark should have a
    single argument, an iterable set of product names in apigee.

    >>> @pytest.mark.product(["personal-demographics-internal-dev"])
    >>> def test_something_with_pds(app_credentials):
    >>>    app_apikey = app_credentials["consumerKey"]
    >>>    app_secret = app_credentials["consumerSecret"]

    See also the `apikey` fixture.
    """

    # https://docs.pytest.org/en/6.2.x/fixture.html#using-markers-to-pass-data-to-fixtures
    products_marker = request.node.get_closest_marker("products")
    if products_marker is None:
        desired_products = []
    else:
        desired_products = products_marker.args[0]

    print(f"desired_products={desired_products}")

    def get_matching_creds(app):
        def approved(x):
            return x["status"] == "approved"

        for creds in filter(approved, app["credentials"]):
            if creds["expiresAt"] == -1 or _now_ms() < creds["expiresAt"]:
                approved_product_names = [p["apiproduct"] for p in filter(approved, creds["apiProducts"])]
                if set(approved_product_names) == set(desired_products):
                    return creds

    current_app_state = test_app()
    matching_creds = get_matching_creds(current_app_state)
    if matching_creds is not None:
        print(f"matching_creds={matching_creds}")
        return matching_creds

    # If we get here, there are not credentials on our test_app,
    # which have access to the EXACT set of desired products requested
    # by the user. So, we use the apigee edge api to add another set
    # of credentials:
    # https://apidocs.apigee.com/docs/developer-apps/1/routes/organizations/%7Borg_name%7D/developers/%7Bdeveloper_email%7D/apps/%7Bapp_name%7D/put

    current_app_state["apiProducts"] = desired_products
    app_url = _apigee_app_base_url + "/" + current_app_state["name"]
    resp = _apigee_edge_session.put(app_url, json=current_app_state)
    assert resp.status_code == 200

    current_app_state = resp.json()
    matching_creds = get_matching_creds(current_app_state)
    assert matching_creds is not None

    print(f"matching_creds={matching_creds}")
    return matching_creds


@pytest.fixture()
def apikey(test_app_credentials):
    """
    Sufficient to access the lightest of our authorization patterns.
    """
    return test_app_credentials["consumerKey"]
