"""
Example tests that show all the features of pytest_nhsd_apim.

They also serve to test the tests themselves.
"""
import json
import logging
import pytest
import requests

LOG = logging.getLogger(__name__)


def test_ping(proxy_base_url):
    """
    Set a request to an open access endpoint.
    """
    resp = requests.get(proxy_base_url + "/_ping")
    assert resp.status_code == 200
    ping_data = json.loads(resp.text)
    assert "version" in ping_data


def test_apikey(proxy_base_url, apikey):
    """
    Ask for an apikey for a product that is subscribed to your proxy.
    This creates a test app and subscribes it to an appropriate
    product behind the scenes.

    If there is no such product, the test will fail.
    """
    LOG.info('test_apikey')
    resp = requests.get(proxy_base_url + "/status-api-key", headers={"apikey": apikey})

    assert resp.status_code == 200


def test_app_apikey_fails_with_invalid_product(apikey):
    LOG.info('test_app_apikey_fails_with_invalid_product')
    url = "https://sandbox.api.service.nhs.uk/hello-world/hello/application"
    resp = requests.get(url,
                        headers={"apikey": apikey},
                        timeout=2)
    assert resp.status_code == 401


@pytest.mark.product_scope("urn:nhsd:apim:user-nhs-login:P0:mock-jwks")
def test_access_token4(proxy_base_url, access_token):
    LOG.info(f'test_access_token4:: {access_token}')
    resp = requests.get(proxy_base_url + "/test-auth/nhs-login/P0",
                        headers={"Authorization": f"Bearer {access_token}"})
    assert resp.text == ''
    assert resp.status_code == 200
    resp = requests.get(proxy_base_url + "/test-auth/nhs-login/P0",
                        headers={"Authorization": f"Bearer {access_token}"})
    assert resp.status_code == 200


@pytest.mark.product_scope("urn:nhsd:apim:app:level3:mock-jwks")
def test_access_token(proxy_base_url, access_token):
    LOG.info(f'test_access_token:: {access_token}')
    resp = requests.get(proxy_base_url + "/test-auth/app/level3",
                        headers={"Authorization": f"Bearer {access_token}"})
    assert resp.status_code == 200


@pytest.mark.product_scope("urn:nhsd:apim:user-nhs-cis2:aal3:mock-jwks", login_method='N3_SMARTCARD')  # N3_SMARTCARD
def test_access_token3(proxy_base_url, access_token):
    LOG.info(f'test_access_token3:: {access_token}')
    resp = requests.get(proxy_base_url + "/test-auth/nhs-cis2/aal3",
                        headers={"Authorization": f"Bearer {access_token}"})
    assert resp.status_code == 200


@pytest.mark.product_scope("urn:nhsd:apim:user-nhs-login:P0:mock-jwks")
def test_access_token_p9(proxy_base_url, access_token):
    expected_result = {"fault": {"faultstring": "Required scope(s): VerifyAccessToken.NHSLoginP9.scopeSet",
                                 "detail": {"errorcode": "steps.oauth.v2.InsufficientScope"}}}
    LOG.info(f'test_access_token:: {access_token}')
    resp = requests.get(proxy_base_url + "/test-auth/nhs-login/P9",
                        headers={"Authorization": f"Bearer {access_token}"})
    assert expected_result == resp.json()
    assert resp.status_code == 403
    resp = requests.get(proxy_base_url + "/test-auth/nhs-login/P0",
                        headers={"Authorization": f"Bearer {access_token}"})
    assert resp.status_code == 200
