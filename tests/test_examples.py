"""

Example tests that show all the features of pytest_nhsd_apim.

They also serve to test the tests themselves.
"""
import pytest
import requests
import json


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
    resp = requests.get(
        proxy_base_url + "/hello/application", headers={"apikey": apikey}
    )

    assert resp.status_code == 200
    assert "Hello Application" in resp.text


def test_app_apikey_fails_with_invalid_product(apikey):
    resp = requests.get(
        "https://sandbox.api.service.nhs.uk/hello-world/hello/application",
        headers={"apikey": apikey},
    )
    assert resp.status_code == 401



@pytest.mark.product_scope("urn:nhsd:apim:user-nhs-id:aal3:hello-world")
def test_products_subscribe_to_two_identity_services(_identity_service_proxy_names):
    assert len(_identity_service_proxy_names) == 2


@pytest.mark.product_scope("urn:nhsd:apim:user-nhs-id:aal3:hello-world")
def test_access_token(proxy_base_url, access_token):
    resp = requests.get(
        proxy_base_url + "/hello/user",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert resp.status_code == 200
    assert "Hello User" in resp.text


@pytest.mark.product_scope("urn:nhsd:apim:user-nhs-id:aal3:hello-world")
def test_access_token2(proxy_base_url, access_token):
    resp = requests.get(
        proxy_base_url + "/hello/user",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert resp.status_code == 200
    assert "Hello User" in resp.text

    
@pytest.mark.product_scope("urn:nhsd:apim:app:level3:hello-world")
def test_access_token3(proxy_base_url, access_token):
    resp = requests.get(
        proxy_base_url + "/hello/user",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert resp.status_code == 200
    assert "Hello User" in resp.text

@pytest.mark.product_scope("urn:nhsd:apim:app:level3:hello-world")
def test_access_token4(proxy_base_url, access_token):
    resp = requests.get(
        proxy_base_url + "/hello/user",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert resp.status_code == 200
    assert "Hello User" in resp.text
    
