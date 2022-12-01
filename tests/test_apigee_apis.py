import pprint

import pytest

from pytest_nhsd_apim.apigee_apis import ApigeeClient, ApiProductsAPI, DebugSessionsAPI, DeveloperAppsAPI, ApigeeNonProdCredentials


@pytest.fixture()
def client():
    config = ApigeeNonProdCredentials()
    return ApigeeClient(config=config)


class TestDeveloperAppsAPI:
    def test_create_app(self, client):
        developer_apps = DeveloperAppsAPI(email="lucas.fantini@nhs.net", client=client)
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
        pprint.pprint(developer_apps.create_app(body=body))

    def test_post_app_by_name(self, client):
        developer_apps = DeveloperAppsAPI(email="lucas.fantini@nhs.net", client=client)
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
        pprint.pprint(developer_apps.post_app_by_name(body=body, app_name="myapp"))

    def test_put_app_by_name(self, client):
        developer_apps = DeveloperAppsAPI(email="lucas.fantini@nhs.net", client=client)
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
        pprint.pprint(developer_apps.put_app_by_name(body=body, app_name="myapp"))

    def test_list_apps(self, client):
        developer_apps = DeveloperAppsAPI(email="lucas.fantini@nhs.net", client=client)
        pprint.pprint(developer_apps.list_apps())

    def test_get_app_by_name(self, client):
        developer_apps = DeveloperAppsAPI(email="lucas.fantini@nhs.net", client=client)
        pprint.pprint(developer_apps.get_app_by_name(app_name="myapp"))

    def test_get_app_attributes(self, client):
        developer_apps = DeveloperAppsAPI(email="lucas.fantini@nhs.net", client=client)
        pprint.pprint(developer_apps.get_app_attributes(app_name="myapp"))

    def test_post_app_attributes(self, client):
        body = {
            "attribute": [
                {"name": "ADMIN_EMAIL", "value": "admin@example.com"},
                {"name": "DisplayName", "value": "My App"},
            ]
        }
        developer_apps = DeveloperAppsAPI(email="lucas.fantini@nhs.net", client=client)
        pprint.pprint(developer_apps.post_app_attributes(app_name="myapp", body=body))

    def test_get_app_attributes_by_name(self, client):
        developer_apps = DeveloperAppsAPI(email="lucas.fantini@nhs.net", client=client)
        pprint.pprint(developer_apps.get_app_attribute_by_name(app_name="myapp", attribute_name="ADMIN_EMAIL"))

    def test_post_app_attribute_by_name(self, client):
        body = {"name": "DisplayName", "value": "MyApp"}
        developer_apps = DeveloperAppsAPI(email="lucas.fantini@nhs.net", client=client)
        pprint.pprint(
            developer_apps.post_app_attribute_by_name(app_name="myapp", attribute_name="DisplayName", body=body)
        )

    def test_delete_app_attribute_by_name(self, client):
        developer_apps = DeveloperAppsAPI(email="lucas.fantini@nhs.net", client=client)
        pprint.pprint(developer_apps.delete_app_attribute_by_name(app_name="myapp", attribute_name="DisplayName"))

    def test_delete_app_by_name(self, client):
        developer_apps = DeveloperAppsAPI(email="lucas.fantini@nhs.net", client=client)
        pprint.pprint(developer_apps.delete_app_by_name(app_name="myapp"))


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
        pprint.pprint(api_products.put_product_by_name(product_name="myapiproduct", body=body))

    def test_get_product_attributes(self, client):
        api_products = ApiProductsAPI(client=client)
        pprint.pprint(api_products.get_product_attributes(product_name="myapiproduct"))

    def test_post_product_attributest(self, client):
        api_products = ApiProductsAPI(client=client)
        body = {"attribute": [{"name": "access", "value": "private"}]}
        pprint.pprint(api_products.post_product_attributest(product_name="myapiproduct", body=body))

    def test_get_product_attribute_by_name(self, client):
        api_products = ApiProductsAPI(client=client)
        pprint.pprint(api_products.get_product_attribute_by_name(product_name="myapiproduct", attribute_name="access"))

    def test_post_product_attribute_by_name(self, client):
        api_products = ApiProductsAPI(client=client)
        body = {"value": "new_value"}
        pprint.pprint(
            api_products.post_product_attribute_by_name(product_name="myapiproduct", attribute_name="access", body=body)
        )

    def test_delete_product_attribute_by_name(self, client):
        api_products = ApiProductsAPI(client=client)
        pprint.pprint(
            api_products.delete_product_attribute_by_name(product_name="myapiproduct", attribute_name="access")
        )

    def test_delete_product_by_name(self, client):
        api_products = ApiProductsAPI(client=client)
        pprint.pprint(api_products.delete_product_by_name(product_name="myapiproduct"))


class TestDebugSessionAPI:
    def test_get_debugsession(self, client):
        debugsession = DebugSessionsAPI(
            client=client, env_name="internal-dev", api_name="mock-jwks-internal-dev", revision_number="17"
        )
        pprint.pprint(debugsession.get_debugsessions())

    def test_post_debugsession(self, client):
        debugsession = DebugSessionsAPI(
            client=client, env_name="internal-dev", api_name="mock-jwks-internal-dev", revision_number="17"
        )
        body = "my_session"
        pprint.pprint(debugsession.post_debugsession(body=body))

    def test_delete_debugsession_by_name(self, client):
        debugsession = DebugSessionsAPI(
            client=client, env_name="internal-dev", api_name="mock-jwks-internal-dev", revision_number="17"
        )

        pprint.pprint(debugsession.delete_debugsession_by_name(session_name="my_session"))

    def test_get_transaction_data(self, client):
        debugsession = DebugSessionsAPI(
            client=client, env_name="internal-dev", api_name="mock-jwks-internal-dev", revision_number="17"
        )
        debugsession.post_debugsession(body="my_session")
        pprint.pprint(debugsession.get_transaction_data(session_name="my_session"))
        debugsession.delete_debugsession_by_name(session_name="my_session")

    def test_get_transaction_data_by_id(self, client):
        # TODO: Need to actually make a request to the proxy to get the transaction_id
        # debugsession = DebugSessionsAPI(
        #     client=client, env_name="internal-dev", api_name="mock-jwks-internal-dev", revision_number="17"
        # )
        # debugsession.post_debugsession(body="my_session")
        # pprint.pprint(debugsession.get_transaction_data_by_id(session_name="my_session", transaction_id="1"))
        # debugsession.delete_debugsession_by_name(session_name="my_session")
        pass
