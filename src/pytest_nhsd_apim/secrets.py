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


@pytest.fixture(scope="session")
@log_method
def _mock_jwks_api_key(_apigee_app_base_url, _apigee_edge_session, test_app):
    creds = get_app_credentials_for_product(
        _apigee_app_base_url, _apigee_edge_session, test_app(), "mock-jwks-internal-dev"
    )
    return creds["consumerKey"]


@pytest.fixture(scope="session")
@log_method
def status_endpoint_auth_headers(_mock_jwks_api_key):
    resp = _SESSION.get(
        "https://internal-dev.api.service.nhs.uk/mock-jwks/status-endpoint-api-key",
        headers={"apikey": _mock_jwks_api_key},
    )
    resp.raise_for_status()
    status_endpoint_api_key = resp.text
    return {"apikey": status_endpoint_api_key}


@pytest.fixture(scope="session")
@log_method
def status_endpoint_api_key(_mock_jwks_api_key):
    resp = _SESSION.get(
        "https://internal-dev.api.service.nhs.uk/mock-jwks/status-endpoint-api-key",
        headers={"apikey": _mock_jwks_api_key},
    )
    resp.raise_for_status()
    return resp.text


@pytest.fixture(scope="session")
@log_method
def _keycloak_client_credentials(_mock_jwks_api_key):
    resp = _SESSION.get(
        "https://internal-dev.api.service.nhs.uk/mock-jwks/keycloak-client-credentials",
        headers={"apikey": _mock_jwks_api_key},
    )
    resp.raise_for_status()
    return resp.json()
