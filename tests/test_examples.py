"""
An example of the tests you can run using pytest_nhsd_apim
"""
import pytest
import requests


@pytest.mark.products(["hello-world-internal-dev"])
def test_app_apikey_works_with_correct_products(apikey):
    """
    Specify the exact set of products you want to be subscribed to.
    Then get the apikey and use it in a request.
    """

    resp = requests.get(
        "https://internal-dev.api.service.nhs.uk/hello-world/hello/application",
        headers={"apikey": apikey},
    )

    assert resp.status_code == 200
    assert "Hello Application" in resp.text


@pytest.mark.products(["hello-world-internal-dev-sandbox"])
def test_app_apikey_fails_with_invalid_products(apikey):
    """
    If the app is subscribed to a product in the wrong environment, we
    should receive a 401.
    """
    resp = requests.get(
        "https://internal-dev.api.service.nhs.uk/hello-world/hello/application",
        headers={"apikey": apikey, "foo": "bar"},
    )
    assert resp.status_code == 401

