"""
The order in wich this tests are ran is important since resources are going to
be created byt the tests in Apigee. A better way writing the tests would be to
create a fixture that manages the creation and tear down of the relevant apps in
every tests but im a bit tired now...
"""
import pprint

import pytest

from pytest_nhsd_apim.apigee_apis import (
    AccessTokensAPI,
    ApigeeClient,
    ApigeeNonProdCredentials,
    ApiProductsAPI,
    DebugSessionsAPI,
    DeveloperAppsAPI,
)


@pytest.fixture()
def client():
    config = ApigeeNonProdCredentials()
    return ApigeeClient(config=config)


class TestDeveloperAppsAPI:
    def test_create_app(self, client):
        developer_apps = DeveloperAppsAPI(client=client)
        body = {
            "apiProducts": ["identity-service-internal-dev"],
            "attributes": [
                {"name": "ADMIN_EMAIL", "value": "lucas.fantini@nhs.net"},
                {"name": "DisplayName", "value": "My App"},
                {"name": "Notes", "value": "Notes for developer app"},
                {"name": "MINT_BILLING_TYPE", "value": "POSTPAID"},
            ],
            "callbackUrl": "example.com",
            "name": "myapp",
            "scopes": [],
            "status": "approved",
        }
        pprint.pprint(
            developer_apps.create_app(email="lucas.fantini@nhs.net", body=body)
        )

    def test_post_app_by_name(self, client):
        developer_apps = DeveloperAppsAPI(client=client)
        body = {
            "apiProducts": ["identity-service-internal-dev"],
            "attributes": [
                {"name": "ADMIN_EMAIL", "value": "lucas.fantini@nhs.net"},
                {"name": "DisplayName", "value": "My App"},
                {"name": "Notes", "value": "Notes for developer app"},
                {"name": "MINT_BILLING_TYPE", "value": "POSTPAID"},
            ],
            "callbackUrl": "new-example.com",
            "name": "myapp",
            "scopes": [],
            "status": "approved",
        }
        pprint.pprint(
            developer_apps.post_app_by_name(
                email="lucas.fantini@nhs.net", body=body, app_name="myapp"
            )
        )

    def test_put_app_by_name(self, client):
        developer_apps = DeveloperAppsAPI(client=client)
        body = {
            "apiProducts": ["identity-service-internal-dev", "mock-jwks-internal-dev"],
            "attributes": [
                {"name": "ADMIN_EMAIL", "value": "lucas.fantini@nhs.net"},
                {"name": "DisplayName", "value": "My App"},
                {"name": "Notes", "value": "Notes for developer app"},
                {"name": "MINT_BILLING_TYPE", "value": "POSTPAID"},
            ],
            "callbackUrl": "new-example.com",
            "name": "myapp",
            "scopes": [],
            "status": "approved",
        }
        pprint.pprint(
            developer_apps.put_app_by_name(
                email="lucas.fantini@nhs.net", body=body, app_name="myapp"
            )
        )

    def test_list_apps(self, client):
        developer_apps = DeveloperAppsAPI(client=client)
        pprint.pprint(developer_apps.list_apps(email="lucas.fantini@nhs.net"))

    def test_get_app_by_name(self, client):
        developer_apps = DeveloperAppsAPI(client=client)
        pprint.pprint(
            developer_apps.get_app_by_name(
                email="lucas.fantini@nhs.net", app_name="myapp"
            )
        )

    def test_get_app_attributes(self, client):
        developer_apps = DeveloperAppsAPI(client=client)
        pprint.pprint(
            developer_apps.get_app_attributes(
                email="lucas.fantini@nhs.net", app_name="myapp"
            )
        )

    def test_post_app_attributes(self, client):
        body = {
            "attribute": [
                {"name": "ADMIN_EMAIL", "value": "admin@example.com"},
                {"name": "DisplayName", "value": "My App"},
            ]
        }
        developer_apps = DeveloperAppsAPI(client=client)
        pprint.pprint(
            developer_apps.post_app_attributes(
                email="lucas.fantini@nhs.net", app_name="myapp", body=body
            )
        )

    def test_get_app_attributes_by_name(self, client):
        developer_apps = DeveloperAppsAPI(client=client)
        pprint.pprint(
            developer_apps.get_app_attribute_by_name(
                email="lucas.fantini@nhs.net",
                app_name="myapp",
                attribute_name="ADMIN_EMAIL",
            )
        )

    def test_post_app_attribute_by_name(self, client):
        body = {"name": "DisplayName", "value": "MyApp"}
        developer_apps = DeveloperAppsAPI(client=client)
        pprint.pprint(
            developer_apps.post_app_attribute_by_name(
                email="lucas.fantini@nhs.net",
                app_name="myapp",
                attribute_name="DisplayName",
                body=body,
            )
        )

    def test_delete_app_attribute_by_name(self, client):
        developer_apps = DeveloperAppsAPI(client=client)
        pprint.pprint(
            developer_apps.delete_app_attribute_by_name(
                email="lucas.fantini@nhs.net",
                app_name="myapp",
                attribute_name="DisplayName",
            )
        )

    def test_delete_app_by_name(self, client):
        developer_apps = DeveloperAppsAPI(client=client)
        pprint.pprint(
            developer_apps.delete_app_by_name(
                email="lucas.fantini@nhs.net", app_name="myapp"
            )
        )


class TestApiProductsAPI:
    def test_get_apiproducts(self, client):
        api_products = ApiProductsAPI(client=client)
        pprint.pprint(api_products.get_products(expand=True))

    def test_post_apiproducts(self, client):
        api_products = ApiProductsAPI(client=client)
        body = {
            "apiResources": ["/"],
            "approvalType": "auto",
            "attributes": [{"name": "access", "value": "public"}],
            "description": "My API product",
            "displayName": "My API product",
            "environments": ["internal-dev"],
            "name": "myapiproduct",
            "proxies": ["identity-service-internal-dev"],
            "scopes": [],
        }
        pprint.pprint(api_products.post_products(body=body))

    def test_get_product_by_name(self, client):
        api_products = ApiProductsAPI(client=client)
        pprint.pprint(api_products.get_product_by_name(product_name="myapiproduct"))

    def test_put_product_by_name(self, client):
        api_products = ApiProductsAPI(client=client)
        body = {
            "apiResources": ["/"],
            "approvalType": "auto",
            "attributes": [{"name": "access", "value": "public"}],
            "description": "My API product",
            "displayName": "My API product",
            "environments": ["internal-dev"],
            "proxies": ["mock-jwks-internal-dev"],
            "scopes": [],
        }
        pprint.pprint(
            api_products.put_product_by_name(product_name="myapiproduct", body=body)
        )

    def test_get_product_attributes(self, client):
        api_products = ApiProductsAPI(client=client)
        pprint.pprint(api_products.get_product_attributes(product_name="myapiproduct"))

    def test_post_product_attributest(self, client):
        api_products = ApiProductsAPI(client=client)
        body = {"attribute": [{"name": "access", "value": "private"}]}
        pprint.pprint(
            api_products.post_product_attributest(
                product_name="myapiproduct", body=body
            )
        )

    def test_get_product_attribute_by_name(self, client):
        api_products = ApiProductsAPI(client=client)
        pprint.pprint(
            api_products.get_product_attribute_by_name(
                product_name="myapiproduct", attribute_name="access"
            )
        )

    def test_post_product_attribute_by_name(self, client):
        api_products = ApiProductsAPI(client=client)
        body = {"value": "new_value"}
        pprint.pprint(
            api_products.post_product_attribute_by_name(
                product_name="myapiproduct", attribute_name="access", body=body
            )
        )

    def test_delete_product_attribute_by_name(self, client):
        api_products = ApiProductsAPI(client=client)
        pprint.pprint(
            api_products.delete_product_attribute_by_name(
                product_name="myapiproduct", attribute_name="access"
            )
        )

    def test_delete_product_by_name(self, client):
        api_products = ApiProductsAPI(client=client)
        pprint.pprint(api_products.delete_product_by_name(product_name="myapiproduct"))


class TestDebugSessionAPI:
    def test_get_debugsession(self, client, _apigee_proxy):
        debugsession = DebugSessionsAPI(
            client=client,
            env_name=_apigee_proxy["environment"],
            api_name=_apigee_proxy["name"],
            revision_number=_apigee_proxy["revision"],
        )
        pprint.pprint(debugsession.get_debugsessions())

    def test_post_debugsession(self, client, _apigee_proxy):
        debugsession = DebugSessionsAPI(
            client=client,
            env_name=_apigee_proxy["environment"],
            api_name=_apigee_proxy["name"],
            revision_number=_apigee_proxy["revision"],
        )
        session = "my_session"
        pprint.pprint(debugsession.post_debugsession(session=session))

    def test_delete_debugsession_by_name(self, client, _apigee_proxy):
        debugsession = DebugSessionsAPI(
            client=client,
            env_name=_apigee_proxy["environment"],
            api_name=_apigee_proxy["name"],
            revision_number=_apigee_proxy["revision"],
        )

        pprint.pprint(
            debugsession.delete_debugsession_by_name(session_name="my_session")
        )

    def test_get_transaction_data(self, client, _apigee_proxy):
        debugsession = DebugSessionsAPI(
            client=client,
            env_name=_apigee_proxy["environment"],
            api_name=_apigee_proxy["name"],
            revision_number=_apigee_proxy["revision"],
        )
        debugsession.post_debugsession(session="my_session")
        pprint.pprint(debugsession.get_transaction_data(session_name="my_session"))
        debugsession.delete_debugsession_by_name(session_name="my_session")

    # get_transaction_data_by_id functionality needs a real test and is tested as part of test_trace in test_examples.py


class TestAccessTokenAPI:
    @pytest.mark.nhsd_apim_authorization({"access": "application", "level": "level3"})
    def test_get_token_details(self, client, _nhsd_apim_auth_token_data):
        # 1. Get an Apigee access_token
        token = _nhsd_apim_auth_token_data["access_token"]
        # 2. Get details
        token_api = AccessTokensAPI(client=client)
        pprint.pprint(token_api.get_token_details(access_token=token))

    @pytest.mark.nhsd_apim_authorization({"access": "application", "level": "level3"})
    def test_post_token_details(self, client, _nhsd_apim_auth_token_data):
        # 1. Get an Apigee access_token
        token = _nhsd_apim_auth_token_data["access_token"]
        # 2. Modify it
        token_api = AccessTokensAPI(client=client)
        body = {
            "scope": "my-malicious-scope",
            "attributes": [
                {"name": "my-malicious-name", "value": "my-malicious-value"}
            ],
        }  # scary...
        pprint.pprint(token_api.post_token_details(access_token=token, body=body))

    @pytest.mark.nhsd_apim_authorization({"access": "application", "level": "level3"})
    def test_delete_token(self, client, _nhsd_apim_auth_token_data):
        # 1. Get an Apigee access_token
        token = _nhsd_apim_auth_token_data["access_token"]
        # 2. Delete it
        token_api = AccessTokensAPI(client=client)
        pprint.pprint(token_api.delete_token(access_token=token))
