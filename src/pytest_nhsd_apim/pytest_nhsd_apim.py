"""
This module defines the high-level interface to pytest-nhsd-apim.

These are the fixtures that should be used by your typical proxy.
Testers are expected to want a low-friction method of successfully
completing the auth journey so they can check their desired access
patterns.

Test applications register with the actual products they define.

e.g.:

    - /pathA is only allowed with a user-restricted access token.

    - /pathB allows both user-restricted and some flavour of
      application-restricted.
"""

import pytest

# Import HOOKS so pytest runs them.
from .config import pytest_addoption, pytest_configure, nhsd_apim_config

# Note: At runtime, pytest does not follow the imports we define in
# our files. Instead it just looks amongst all the things it found
# when it imported our extension.  This means we have to import *all*
# of our fixtures into this module even if they are only called as
# dependencies of our "public" fixtures.
from .apigee_edge import (
    _apigee_edge_session,
    _proxy_name,
    _apigee_app_base_url,
    _apigee_proxy,
    _proxy_products,
    _scope,
    _proxy_product_with_scope,
    test_app,
    _test_app_credentials,
    _apigee_edge_session,
    _apigee_products,
    _create_test_app,
    _test_app_callback_url,
)

from . import auth_journey


@pytest.fixture(scope="session")
def proxy_url(_apigee_proxy):
    """
    The full URL of the proxy under test.
    """
    env = _apigee_proxy["environment"]
    prefix = "https://"
    if env != "prod":
        prefix = prefix + f"{env}."
    return prefix + "api.service.nhs.uk/" + _apigee_proxy["basepaths"][0]


@pytest.fixture()
def apikey(_test_app_credentials):
    """
    Assuming a product exists on Apigee that grants access to your
    API.  This fixture will register a test app with that product and
    return the apikey.

    This 'apikey' is sometimes called the 'client_id' or 'consumerKey'
    depending on the context.

    This is sufficient to access some application restricted APIs.
    """
    return _test_app_credentials["consumerKey"]


@pytest.fixture(scope="session")
def _identity_service_base_url():
    # TODO make this dynamic...
    # oauth2 or oauth2-mock for internal-dev/int
    return f"https://internal-dev.api.service.nhs.uk/oauth2"


@pytest.fixture()
def _user_restricted_access_token(
    _scope, _test_app_credentials, _test_app_callback_url, _identity_service_base_url
):
    if not _scope.startswith("urn:nhsd:apim:user"):
        return None

    return auth_journey.get_user_restricted_access_token(
        _identity_service_base_url,
        _test_app_credentials["consumerKey"],
        _test_app_credentials["consumerSecret"],
        _test_app_callback_url,
    )


@pytest.fixture()
def _signed_jwt_access_token():
    return None


@pytest.fixture()
def access_token(_signed_jwt_access_token, _user_restricted_access_token):

    if _signed_jwt_access_token:
        return _signed_jwt_access_token
    elif _user_restricted_access_token:
        return _user_restricted_access_token
