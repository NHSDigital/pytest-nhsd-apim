"""

Example tests that show all the features of pytest_nhsd_apim.

They also serve to test the tests themselves.
"""
import pytest
import requests
import json

@pytest.mark.skip(reason="testing")
def test_ping(proxy_base_url):
    """
    Set a request to an open access endpoint.
    """
    resp = requests.get(proxy_base_url + "/_ping")
    assert resp.status_code == 200
    ping_data = json.loads(resp.text)
    assert "version" in ping_data


@pytest.mark.skip(reason="testing")
def test_app_apikey_works_with_correct_product(proxy_base_url, apikey):
    """
    Ask for an apikey for a product that is subscribed to your proxy.
    This creates a test app and subscribes it to an appropriate
    product behind the scenes.

    If there is no such product, the test will fail.
    """
    resp = requests.get(proxy_base_url + "/hello/application", headers={"apikey": apikey})

    assert resp.status_code == 200
    assert "Hello Application" in resp.text



@pytest.mark.skip(reason="testing")
def test_app_apikey_fails_with_invalid_product(apikey):
    """
    Here we send a request to the wrong proxy to confirm, indeed we
    get rejected.
    """
    resp = requests.get(
        "https://sandbox.api.service.nhs.uk/hello-world/hello/application",
        headers={"apikey": apikey},
    )
    assert resp.status_code == 401

@pytest.mark.product_scope("urn:nhsd:apim:user-nhs-id:aal3:hello-world")
def test_products_subscribe_to_two_identity_services(_identity_service_proxy_names):
    assert len(_identity_service_proxy_names) == 2

# @pytest.mark.product_scope("urn:nhsd:apim:user-nhs-id:aal3:hello-world")
# def test_pytest_extension_prefers_mock_identity_service_proxies(_identity_service_proxy_name):
#     assert "mock" in _identity_service_proxy_name


# @pytest.mark.product_scope("urn:nhsd:apim:app:level3:hello-world")
@pytest.mark.product_scope("urn:nhsd:apim:user-nhs-id:aal3:hello-world")
# @pytest.mark.product_scope("urn:nhsd:apim:user-nhs-login:P0:hello-world")
def test_access_token_magic_works(proxy_base_url, access_token):
    """
    The access_token fixture does the hard work of the authorization
    journey for you.

    It will figure out the correct product from the scope you provide
    via the pytest.mark.product_scope.  (This should line up with one
    of the products in your manifest file!)

    If you pick a product_scope implying user restricted, it will do
    the three-legged oauth for you.

    If you pick a product scope implying an application-restricted
    pattern it do signed-jwt authentication.
    """
    resp = requests.get(
        proxy_base_url + "/hello/user",
        headers={"Authorization": f"Bearer {access_token}", "foo": "bar"}
    )
    assert resp.status_code == 200
    assert "Hello User" in resp.text
