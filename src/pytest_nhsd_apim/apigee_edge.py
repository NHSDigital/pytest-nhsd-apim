"""
Fixtures which interact with Apigee Edge API.

This includes app setup/teardown, getting proxy info (proxy-under-test
+ identity-service of choice), getting products, registering them with
the test app.
"""
from typing import Callable
from uuid import uuid4
from datetime import datetime

import requests
import pytest

from .config import nhsd_apim_config
from .auth_journey import jwt_public_key_url

APIGEE_BASE_URL = "https://api.enterprise.apigee.com/v1/"


@pytest.fixture(scope="session")
def _apigee_edge_session(nhsd_apim_config):
    """
    A requests session with the correct auth header.
    """
    token = nhsd_apim_config["APIGEE_ACCESS_TOKEN"]
    session = requests.session()
    session.headers = {"Authorization": f"Bearer {token}"}
    return session


@pytest.fixture(scope="session")
def _proxy_name(nhsd_apim_config):
    return nhsd_apim_config["APIGEE_PROXY_NAME"]


@pytest.fixture(scope="session")
def _apigee_app_base_url(nhsd_apim_config):
    org = nhsd_apim_config["APIGEE_ORGANIZATION"]
    dev = nhsd_apim_config["APIGEE_DEVELOPER"]
    url = APIGEE_BASE_URL + f"organizations/{org}/developers/{dev}/apps"
    return url


def _get_proxy_json(session, proxy_base_url):
    """
    Query the apigee edge API to get data about the desired proxy, in particular it's current deployment.
    """
    deployment_resp = session.get(proxy_base_url + "/deployments")
    deployment_json = deployment_resp.json()

    # Should be the case
    assert len(deployment_json["environment"]) == 1

    deployed_revision = next(
        filter(
            lambda d: d["state"] == "deployed",
            deployment_json["environment"][0]["revision"]
        )
    )
    revision = deployed_revision["name"]
    proxy_resp = session.get(proxy_base_url + f"/revisions/{revision}")
    assert proxy_resp.status_code == 200
    proxy_json = proxy_resp.json()
    proxy_json["environment"] = deployment_json["environment"][0]["name"]
    return proxy_json


@pytest.fixture()
def _identity_service_proxy(
    _apigee_edge_session, nhsd_apim_config, _identity_service_proxy_name
):
    """
    Get the current revision deployed and pull proxy metadata.
    """
    org = nhsd_apim_config["APIGEE_ORGANIZATION"]
    url = APIGEE_BASE_URL + f"organizations/{org}/apis/{_identity_service_proxy_name}"
    return _get_proxy_json(_apigee_edge_session, url)


@pytest.fixture(scope="session")
def _apigee_proxy(_apigee_edge_session, nhsd_apim_config):
    """
    Get the current revision deployed and pull proxy metadata.
    """
    org = nhsd_apim_config["APIGEE_ORGANIZATION"]
    proxy_name = nhsd_apim_config["APIGEE_PROXY_NAME"]
    proxy_base_url = APIGEE_BASE_URL + f"organizations/{org}/apis/{proxy_name}"
    return _get_proxy_json(_apigee_edge_session, proxy_base_url)


@pytest.fixture(scope="session")
def _proxy_products(_proxy_name, _apigee_products):
    """
    Find all products that grant access to your proxy (by name).

    In the case of open-access to an API, ensure this is not called as
    it raises an exception when there are no matches.

    This also allows us to skip checking whether the returned list is
    empty in other fixtures.
    """
    proxy_products = [
        product for product in _apigee_products if _proxy_name in product["proxies"]
    ]
    if len(proxy_products) == 0:
        raise ValueError(f"No products grant access to proxy {_proxy_name}")
    return proxy_products


def _get_proxy_url(proxy_json):
    """
    Construct the proxy url from the proxy_json
    """
    env = proxy_json["environment"]
    prefix = "https://"
    if env != "prod":
        prefix = prefix + f"{env}."
    return prefix + "api.service.nhs.uk/" + proxy_json["basepaths"][0]


@pytest.fixture(scope="session")
def proxy_base_url(_apigee_proxy):
    """
    Base URL of the proxy under test.
    """
    return _get_proxy_url(_apigee_proxy)


@pytest.fixture()
def identity_service_base_url(_identity_service_proxy):
    """
    Base URL of the identity-service proxy we will use to authenticate.
    """
    return _get_proxy_url(_identity_service_proxy)


@pytest.fixture()
def _scope(request):
    """
    Mark your test with a product_scope marker, to ensure that your
    access_token is derived from a product with the correct scope.

    >>> import requests
    >>> @pytest.mark.product_scope('urn:nhsd:apim:user-nhs-id:aal3:personal-demographics-service')
    >>> def test_application_restricted_access(proxy_url, access_token):
    >>>     resp = requests.get(proxy_url + "/a/path/that/is/application/restricted",
    >>>                         headers={"Authorization": f"Bearer {access_token}"})
    >>>     assert resp.status_code == 200
    """
    marker = request.node.get_closest_marker("product_scope")
    if marker is None:
        return None
    if len(marker.args) < 1:
        raise ValueError(
            "pytest.marker.product_scope requires one positional arg 'scope'"
        )
    return str(marker.args[0])


@pytest.fixture()
def _identity_service_proxy_names(_proxy_product_with_scope):
    return [
        proxy
        for proxy in _proxy_product_with_scope["proxies"]
        if proxy.startswith("identity-service")
    ]


@pytest.fixture()
def _identity_service_proxy_name(_identity_service_proxy_names):
    """
    Make a reasonable choice about which identity-service proxy to
    use.

    We have a very dumb 'simulated_auth' app, which was the original
    and is typically what our internal environments point to.

    Second, and definitively better, we have a keycloak instance,
    which is a proper OIDC provider, which is pointed to by
    identity-service proxies with "mock" in the name.

    Prefer keycloak over simulated auth.  Return None if there's no
    identity-service proxies, though this should probably never
    happen.
    """
    if not _identity_service_proxy_names:  # empty list
        return None

    # prefer one with "mock" in the name.
    keycloak = next(
        filter(lambda name: not "-mock" in name, _identity_service_proxy_names), None
    )
    if keycloak:
        return keycloak

    return _identity_service_proxy_names[0]


@pytest.fixture()
def _proxy_product_with_scope(_scope, _proxy_products, _proxy_name):
    """
    The first product with a scope matching the one specified by the
    pytest.marker.product_scope fixture.

    If the required _scope is None then just returns the first
    product.  Otherwise finds a product that has the required scope.

    Raises an exception if there are no matches.

    This allows us to assume (in other fixtures) that this function
    always returns a product.
    """
    if _scope is None:
        # Any product referencing the proxy under test is fine, so
        # return the first one.
        return _proxy_products[0]
    for product in _proxy_products:
        if _scope in product["scopes"]:
            return product
    raise ValueError(
        f"No product granting access to proxy under test has scope {_scope}"
    )


@pytest.fixture()
def test_app(_create_test_app, _apigee_edge_session, _apigee_app_base_url) -> Callable:
    """
    A Callable that gets you the current state of the test app.
    """
    # pytest fixtures are wonderful, and do lots of magical things.
    #
    # But...
    #
    # In any well developed pytest extension, one ends up with a
    # complicated dependency graph of fixtures calling fixtures
    # calling fixtures. In some of these fixtures we want the
    # "current-state" of our app. But some fixtures we want to update
    # the state of the app. Which fixture gets called first?
    # The answer is... it's really hard to know.
    #
    # As much as I love pytest-provided caching, it's safest to let
    # Apigee be the sole arbiter of the current state of our test app
    # at the cost of an API call.  Therefore I'm returning a callable
    # rather than JSON from this fixture.
    #
    # In any case, if we get the higher level abstrations right in
    # this pytest-extension, a run-of-the-mill user won't need to know
    # much about the app at all, they will just have credentials to
    # call their api.
    def app():
        resp = _apigee_edge_session.get(
            _apigee_app_base_url + "/" + _create_test_app["name"]
        )
        return resp.json()

    return app


@pytest.fixture()
def _test_app_credentials(
    _apigee_app_base_url,
    _apigee_edge_session,
    test_app,
    _scope,
    _proxy_product_with_scope,
):
    def get_matching_creds(app):
        def approved(x):
            return x["status"] == "approved"

        now = int(1000 * datetime.utcnow().timestamp())
        for creds in filter(approved, app["credentials"]):
            if creds["expiresAt"] == -1 or now < creds["expiresAt"]:
                approved_product_names = [
                    p["apiproduct"] for p in filter(approved, creds["apiProducts"])
                ]
                if _proxy_product_with_scope["name"] in approved_product_names:
                    return creds

    current_app_state = test_app()
    matching_creds = get_matching_creds(current_app_state)
    if matching_creds is not None:
        return matching_creds

    # If we get here, there are not credentials on our test_app,
    # which have access to the EXACT set of desired products requested
    # by the user. So, we use the apigee edge api to add another set
    # of credentials:
    # https://apidocs.apigee.com/docs/developer-apps/1/routes/organizations/%7Borg_name%7D/developers/%7Bdeveloper_email%7D/apps/%7Bapp_name%7D/put

    current_app_state["apiProducts"] = [_proxy_product_with_scope["name"]]
    app_url = _apigee_app_base_url + "/" + current_app_state["name"]
    resp = _apigee_edge_session.put(app_url, json=current_app_state)
    if resp.status_code != 200:
        raise ValueError(
            f"Unexpected response from {app_url}: {resp.status_code}, {resp.text}"
        )

    current_app_state = resp.json()
    matching_creds = get_matching_creds(current_app_state)
    return matching_creds


@pytest.fixture(scope="session")
def _apigee_edge_session(nhsd_apim_config):
    token = nhsd_apim_config["APIGEE_ACCESS_TOKEN"]
    session = requests.session()
    session.headers = {"Authorization": f"Bearer {token}"}
    return session


@pytest.fixture(scope="session")
def _apigee_products(_apigee_edge_session, nhsd_apim_config):
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
def _create_test_app(_apigee_app_base_url, _apigee_edge_session, jwt_public_key_url):
    """
    Create an ephemeral app that lasts the duration of the pytest
    session.

    Note that a single app can have many sets of credentials.  Each
    set of credentials can be subscribed to a unique set of products,
    so one app can test your API against multiple product
    configurations should you need to do so.  See `app_credentials`
    for details.
    """

    app = {
        "name": f"apim-auto-{uuid4()}",
        "callbackUrl": "https://example.org/callback",
        "attributes": [{"name": "jwks-resource-url", "value": jwt_public_key_url}],
    }
    create_resp = _apigee_edge_session.post(_apigee_app_base_url, json=app)
    assert create_resp.status_code == 201

    yield create_resp.json()
    delete_resp = _apigee_edge_session.delete(_apigee_app_base_url + "/" + app["name"])
    assert delete_resp.status_code == 200


@pytest.fixture(scope="session")
def _test_app_callback_url(_create_test_app):
    return _create_test_app["callbackUrl"]
