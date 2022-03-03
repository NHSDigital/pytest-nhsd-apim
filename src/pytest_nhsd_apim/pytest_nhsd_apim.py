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
import logging

import pytest

# Import HOOKS so pytest runs them.
from .config import pytest_addoption, pytest_configure, nhsd_apim_config

# Note: At runtime, pytest does not follow the imports we define in
# our files. Instead, it just looks amongst all the things it found
# when it imported our extension.  This means we have to import *all*
# of our fixtures into this module even if they are only called as
# dependencies of our public fixtures.
from .apigee_edge import (
    _apigee_edge_session,
    _auth_journey,
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
    _identity_service_proxy_names,
    _identity_service_proxy_name,
    _identity_service_proxy,
    proxy_base_url,
    identity_service_base_url,
)

from .auth_journey import (
    get_access_token_via_user_restricted_flow,
    get_access_token_via_signed_jwt_flow,
    _jwt_keys,
    jwt_private_key_pem,
    jwt_public_key_pem,
    jwt_public_key,
    jwt_public_key_id,
    jwt_public_key_url,
)

LOG = logging.getLogger(__name__)


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


@pytest.fixture()
def access_token(
        _auth_journey,
        _test_app_credentials,
        _test_app_callback_url,
        identity_service_base_url,
        jwt_private_key_pem,
        jwt_public_key_id):
    """
    The main fixture.
    """
    if _auth_journey['scope'].startswith("urn:nhsd:apim:user"):
        auth_scope, permission_lvl = _auth_journey['scope'].split(":")[3:5]
        auth_scope = auth_scope[5:]  # nhs-login, nhs-cis2

        if '-id' in auth_scope:
            auth_scope = auth_scope.replace('id', 'cis2')
        if 'cis2' in auth_scope and 'aal3' in permission_lvl:
            permission_lvl = _auth_journey.get('login_method', 'N3_SMARTCARD')
        LOG.debug(f'auth_scope is:: {auth_scope} - {permission_lvl}')
        return get_access_token_via_user_restricted_flow(
            identity_service_base_url,
            _test_app_credentials["consumerKey"],
            _test_app_credentials["consumerSecret"],
            _test_app_callback_url,
            auth_scope=auth_scope,
            permission_lvl=permission_lvl)

    if _auth_journey['scope'].startswith("urn:nhsd:apim:app"):
        return get_access_token_via_signed_jwt_flow(
            identity_service_base_url,
            _test_app_credentials["consumerKey"],
            jwt_private_key_pem,
            jwt_public_key_id)

    raise RuntimeError("Shouldn't get here")
