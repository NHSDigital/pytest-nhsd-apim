"""
An example of the tests you can run using pytest_nhsd_apim
"""
import pytest
import requests
import json

@pytest.mark.skip(reason="testing")
def test_ping(proxy_url):
    """
    Set a request to an open access endpoint.
    """
    resp = requests.get(proxy_url + "/_ping")
    assert resp.status_code == 200
    ping_data = json.loads(resp.text)
    assert "version" in ping_data


@pytest.mark.skip(reason="testing")
def test_app_apikey_works_with_correct_product(proxy_url, apikey):
    """
    Ask for an apikey for a product that is subscribed to your proxy.
    This creates a test app and subscribes it to an appropriate
    product behind the scenes.

    If there is no such product, the test will fail.
    """
    resp = requests.get(proxy_url + "/hello/application", headers={"apikey": apikey})

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
def test_access_token_magic_works(proxy_url, access_token):
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
        proxy_url + "/hello/user",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert resp.status_code == 200
    assert "Hello User" in resp.text
