"""
The mock-jwks proxy is wired up to pull secrets from an encrypted KVM.
The content of which is set in the infrastructure repository, which
pulls the secrets from AWS secretsmanager.
"""

import pytest
import requests

from .apigee_edge import (
    _apigee_app_base_url,
    _apigee_edge_session,
    get_app_credentials_for_product,
    test_app,
)

from .log import log, log_method


_SESSION = requests.session()


@pytest.fixture()
@log_method
def _mock_jwks_api_key(_apigee_app_base_url, _apigee_edge_session, test_app):
    creds = get_app_credentials_for_product(
        _apigee_app_base_url, _apigee_edge_session, test_app(), "mock-jwks-internal-dev"
    )
    return creds["consumerKey"]


@pytest.fixture()
@log_method
def status_endpoint_auth_headers(_status_endpoint_api_key):
    return {"apikey": _status_endpoint_api_key}


_STATUS_ENDPOINT_API_KEY = None

@pytest.fixture()
@log_method
def _status_endpoint_api_key(_mock_jwks_api_key):
    global _STATUS_ENDPOINT_API_KEY
    if _STATUS_ENDPOINT_API_KEY is None:
        resp = _SESSION.get(
            "https://internal-dev.api.service.nhs.uk/mock-jwks/status-endpoint-api-key",
            headers={"apikey": _mock_jwks_api_key},
        )
        resp.raise_for_status()
        _STATUS_ENDPOINT_API_KEY = resp.text
    return _STATUS_ENDPOINT_API_KEY


_KEYCLOAK_CLIENT_CREDENTIALS = None

@pytest.fixture()
@log_method
def _keycloak_client_credentials(_mock_jwks_api_key):
    global _KEYCLOAK_CLIENT_CREDENTIALS
    if _KEYCLOAK_CLIENT_CREDENTIALS is None:
        resp = _SESSION.get(
            "https://internal-dev.api.service.nhs.uk/mock-jwks/keycloak-client-credentials",
            headers={"apikey": _mock_jwks_api_key},
        )
        resp.raise_for_status()
        _KEYCLOAK_CLIENT_CREDENTIALS = resp.json()
    return _KEYCLOAK_CLIENT_CREDENTIALS
