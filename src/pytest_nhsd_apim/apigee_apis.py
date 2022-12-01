from abc import ABC, abstractmethod
from typing import Optional, Union

import jwt
import pyotp
import requests
from jwt import ExpiredSignatureError
from pydantic import BaseSettings, root_validator



class ApigeeProdCredentials(BaseSettings):
    """
    Reads auth_server/username/password/passcode/otp_uri from environment
    variables.

    These control what we send to the auth server.  Required environment
    variables depends on who is authenticating and the mechanism.

    All environment variables in the table below are prefixed with
    APIGEE_NHSD_NONPROD_ for nhsd-nonprod and, imaginatively,
    APIGEE_NHSD_PROD_ for nhsd-prod.  so AUTH_SERVER for prod =
    APIGEE_NHSD_PROD_AUTH_SERVER.

    |------------------------+---------------------------------|
    | Auth/user combo        | Required environment variables  |
    |------------------------+---------------------------------|
    | non-SAML               | USERNAME, PASSWORD, OTP_KEY     |
    | SAML machine users     | AUTH_SERVER, USERNAME, PASSWORD |
    | SAML non-machine users | AUTH_SERVER, PASSCODE           |
    |------------------------+---------------------------------|

    No attempt is made to recover if in invalid combination of environment
    variables is provided.
    """
    auth_server: str = "nhs-digital-prod.login.apigee.com"
    apigee_nhsd_prod_username: Optional[str] = None
    apigee_nhsd_prod_password: Optional[str] = None
    apigee_nhsd_prod_passcode: Optional[str] = None
    apigee_access_token: Optional[str] = None

    @root_validator(allow_reuse=True)
    def check_credentials_config(cls, values):
        if all(
            [
                values.get(key)
                for key in ["apigee_nhsd_prod_username", "apigee_nhsd_prod_password", "apigee_nhsd_prod_passcode"]
            ]
        ):
            values["auth_method"] = "saml"
            return values
        elif all([values.get(key) for key in ["apigee_nhsd_prod_username", "apigee_nhsd_prod_password"]]):
            values["auth_method"] = "saml"
            return values
        elif values["access_token"]:
            values["auth_method"] = "access_token"
            return values
        else:
            raise ValueError("Please provide valid credentials or an access_token")

    class Config:
        env_prefix = "apigee_nhsd_prod_"

    @property
    def auth_method(self):
        pass

    @property
    def org(self):
        return "nhsd-prod"

    @property
    def host(self):
        return "api.enterprise.apigee.com"

    @property
    def base_path(self):
        return f"/v1/organizations/{self.org}"

    @property
    def base_url(self):
        return f"https://{self.host}{self.base_path}"

    @property
    def data(self):
        data = {"grant_type": "password", "response_type": "token"}
        if self.apigee_nhsd_prod_passcode:
            data["passcode"] = self.apigee_nhsd_prod_passcode
        else:
            data["username"] = self.apigee_nhsd_prod_username
            data["password"] = self.apigee_nhsd_prod_password
        return data

    @property
    def params(self):
        return None


class ApigeeNonProdCredentials(BaseSettings):
    """
    Reads auth_server/username/password/passcode/otp_uri from environment
    variables.

    These control what we send to the auth server.  Required environment
    variables depends on who is authenticating and the mechanism.

    All environment variables in the table below are prefixed with
    APIGEE_NHSD_NONPROD_ for nhsd-nonprod and, imaginatively,
    APIGEE_NHSD_PROD_ for nhsd-prod.  so AUTH_SERVER for prod =
    APIGEE_NHSD_PROD_AUTH_SERVER.

    |------------------------+---------------------------------|
    | Auth/user combo        | Required environment variables  |
    |------------------------+---------------------------------|
    | non-SAML               | USERNAME, PASSWORD, OTP_KEY     |
    | SAML machine users     | AUTH_SERVER, USERNAME, PASSWORD |
    | SAML non-machine users | AUTH_SERVER, PASSCODE           |
    |------------------------+---------------------------------|

    No attempt is made to recover if in invalid combination of environment
    variables is provided.
    """
    auth_server: str = "login.apigee.com"
    apigee_nhsd_nonprod_username: Optional[str]
    apigee_nhsd_nonprod_password: Optional[str]
    apigee_nhsd_nonprod_otp_key: Optional[str]
    apigee_access_token: Optional[str]

    @root_validator(allow_reuse=True)
    def check_credentials_config(cls, values):
        if all(
            [
                values.get(key)
                for key in [
                    "apigee_nhsd_nonprod_username",
                    "apigee_nhsd_nonprod_password",
                    "apigee_nhsd_nonprod_otp_key",
                ]
            ]
        ):
            values["auth_method"] = "saml"
            return values
        elif values["apigee_access_token"]:
            values["auth_method"] = "access_token"
            return values
        else:
            raise ValueError("Please provide valid credentials or an access_token")

    @property
    def org(self):
        return "nhsd-nonprod"

    @property
    def host(self):
        return "api.enterprise.apigee.com"

    @property
    def base_path(self):
        return f"/v1/organizations/{self.org}"

    @property
    def base_url(self):
        return f"https://{self.host}{self.base_path}"

    @property
    def data(self):
        return {
            "grant_type": "password",
            "response_type": "token",
            "username": self.apigee_nhsd_nonprod_username,
            "password": self.apigee_nhsd_nonprod_password,
        }

    @property
    def params(self):
        if not self.apigee_nhsd_nonprod_otp_key:
            return None
        otp = pyotp.parse_uri(
            f"otpauth://totp/{self.apigee_nhsd_nonprod_username}?secret={self.apigee_nhsd_nonprod_otp_key}"
        )
        return {"mfa_token": otp.now()}


class ApigeeAuthenticator:
    def __init__(self, config: Union[ApigeeNonProdCredentials, ApigeeProdCredentials]) -> None:
        self.config = config

    def get_token(self):
        """
        Send a POST request to the authorization server.

        Specify the auth server via environment vars:
        - APIGEE_NHSD_NONPROD_AUTH_SERVER
        - APIGEE_NHSD_PROD_AUTH_SERVER
        If not provided, defaults to non-SAML 'login.apigee.com'.
        """
        if self.config.auth_method == "saml":
            SESSION = requests.Session()
            url = f"https://{self.config.auth_server}/oauth/token"
            resp = SESSION.post(
                url=url,
                params=self.config.params,
                headers={"Authorization": "Basic ZWRnZWNsaTplZGdlY2xpc2VjcmV0", "Accept": "application/json"},
                data=self.config.data,
            )
            try:
                resp.raise_for_status()
                return resp.json()["access_token"]
            except requests.HTTPError as e:  # TODO some more fancy error message...
                raise e
        else:
            return self.config.apigee_access_token


class RestClient(ABC):
    """Defines a generic rest client interface"""

    @property
    @abstractmethod
    def base_url(self):
        pass

    @property
    @abstractmethod
    def org(self):
        pass

    @abstractmethod
    def is_authenticated(self):
        pass

    @abstractmethod
    def authenticate(self):
        pass

    @abstractmethod
    def get(self):
        pass

    @abstractmethod
    def post(self):
        pass

    @abstractmethod
    def put(self):
        pass

    @abstractmethod
    def delete(self):
        pass


class ApigeeClient(RestClient):
    """
    Apigee authenticated client. Before each operation (GET, POST, PUT, DELETE)
    the client checks for the self.token: if it is none, then it gets one using
    the authenticator, if there is one then it checks is not expired... if it is
    then gets a new one using the authenticator. Otherwise uses the existing
    valid access token
    """

    def __init__(self, config: Union[ApigeeNonProdCredentials, ApigeeProdCredentials]) -> None:
        self.token = None
        self.config = config
        self.authenticator = ApigeeAuthenticator(config=config)

    def authenticate(self):
        self.token = self.authenticator.get_token()
        return self.token

    def _session(self, *args, **kwargs) -> requests.Session:
        """ Creates an authenticated session """
        session = requests.session()
        session.headers.update({"Authorization": f"Bearer {self.token}"})
        return session

    @property
    def base_url(self):
        return self.config.base_url

    @property
    def org(self):
        return self.config.org

    def is_authenticated(self):
        if self.token:
            # Verify the token is still valid...
            options = {"verify_signature": False, "verify_aud": False, "verify_exp": True}
            try:
                jwt.decode(self.token, options=options)
                return True
            except ExpiredSignatureError:
                return False
        return False

    def get(self, *args, **kwargs) -> requests.Response:
        if not self.is_authenticated():
            self.authenticate()
        return self._session().get(*args, **kwargs)

    def post(self, *args, **kwargs) -> requests.Response:
        if not self.is_authenticated():
            self.authenticate()
        return self._session().post(*args, **kwargs)

    def put(self, *args, **kwargs) -> requests.Response:
        if not self.is_authenticated():
            self.authenticate()
        return self._session().put(*args, **kwargs)

    def delete(self, *args, **kwargs) -> requests.Response:
        if not self.is_authenticated():
            self.authenticate()
        return self._session().delete(*args, **kwargs)


class DeveloperAppsAPI:
    """Manage developers that register apps."""

    def __init__(self, email: str, client: RestClient) -> None:
        self.client = client
        self.email = email

    def list_apps(self, **query_params) -> "list[str]":
        """
        Lists all apps created by a developer in an organization. Optionally,
        you can expand the response to include the profile for each app.

        With Apigee Edge for Public Cloud:

        A maximum of 100 developer apps are returned per API call. You can
        paginate the list of developer apps returned using the startKey and
        count query parameters.
        """
        params = query_params
        resource = f"/developers/{self.email}/apps"
        url = f"{self.client.base_url}{resource}"
        resp = self.client.get(url=url, params=params)
        if resp.status_code != 200:
            raise Exception(
                f"GET request to {resp.url} failed with status_code: {resp.status_code}, Reason: {resp.reason} and Content: {resp.text}"
            )
        return resp.json()

    def create_app(self, body: dict) -> "dict":
        """
        Creates an app associated with a developer, associates the app with an
        API product, and auto-generates an API key for the app to use in calls
        to API proxies inside the API product.

        The name is the unique ID of the app that you can use in Edge API calls.
        The DisplayName (set with an attribute) is what appears in the Edge UI.
        If you don't provide a DisplayName, the name is used.

        The keyExpiresIn property sets the expiration on the API key. If you
        don't set a value or set the value to -1, the API key never expires.

        Ensure optimal API product and app security

        An organization-level property,
        features.keymanagement.disable.unbounded.permissions, strengthens the
        security of API products in verifying API calls. When the property is
        set to true, the following features are enforced.

        App creation: When creating a developer or company app, the Edge API
        requires that the app be associated with an API product. (The Edge UI
        already enforces this.)

        API product configuration: To create or update an API product, the API
        product must include at least one API proxy or a resource path in its
        definition.

        Runtime security: API calls are rejected by an API product in the
        following situations:

        An API product doesn't include at least one API proxy or resource path.

        If the flow.resource.name variable in the message doesn't include a
        resource path that the API product can evaluate.

        If the app making the API call isn't associated with an API product.

        Note: Setting this organization property requires system administrator
        privileges. Edge for Private Cloud system administrators can add this
        property when updating organization properties. If you are an Edge for
        Public Cloud user, contact Apigee Support to set the organization
        property.
        """

        resource = f"/developers/{self.email}/apps"
        url = f"{self.client.base_url}{resource}"
        resp = self.client.post(url=url, json=body)
        if resp.status_code != 201:
            raise Exception(
                f"POST request to {resp.url} failed with status_code: {resp.status_code}, Reason: {resp.reason} and Content: {resp.text}"
            )
        return resp.json()

    def get_app_by_name(self, app_name: str, **query_params) -> "dict":
        """Gets the profile of a specific developer app."""

        params = query_params
        resource = f"/developers/{self.email}/apps/{app_name}"
        url = f"{self.client.base_url}{resource}"
        resp = self.client.get(url=url, params=params)
        if resp.status_code != 200:
            raise Exception(
                f"GET request to {resp.url} failed with status_code: {resp.status_code}, Reason: {resp.reason} and Content: {resp.text}"
            )
        return resp.json()

    def post_app_by_name(self, app_name: str, body: dict) -> "dict":
        """
        Approves, revokes, or generates an API key for a developer app.

        To approve or revoke the API key for a developer app, set status to
        approve or revoke in the request body.

        Note: As a convenience, you can call the API with the action query
        parameter set to approve or revoke (with no request body) and set the
        Content-type header to application/octet-stream. In this case, the HTTP
        status code for success is: 204 No Content

        To generate a new consumer key and consumer secret for the developer
        app, pass the required details, such as API products, in the request
        body. Rather than replace an existing key, the API generates a new key.

        For example, if you're using API key rotation, you can generate new keys
        with expiration times that overlap keys that will be out of rotation
        when they expire. You might also generate a new key/secret if the
        security of the original key/secret is compromised. After the new API
        key is generated, multiple key pairs will be associated with a single
        app. Each key pair has an independent status (revoked or approved) and
        an independent expiration time. Any non-expired, approved key can be
        used in an API call. You should revoke an API key that has been
        compromised.

        Note: You must include all current attribute and callback values in the
        payload; otherwise, the existing values are removed.

        If you want to set the consumer key and consumer secret rather than
        having Edge generate them randomly, see Import existing consumer keys
        and secrets. (However, that API does not let you set an expiration
        time.)
        """

        resource = f"/developers/{self.email}/apps/{app_name}"
        url = f"{self.client.base_url}{resource}"
        resp = self.client.post(url=url, json=body)
        if resp.status_code != 200:
            raise Exception(
                f"POST request to {resp.url} failed with status_code: {resp.status_code}, Reason: {resp.reason} and Content: {resp.text}"
            )
        return resp.json()

    def put_app_by_name(self, app_name: str, body: dict) -> "dict":
        """
        Updates an existing developer app.

        You can add an app to an API product with this API, which automatically
        generates an API key for the app to use when calling APIs in the
        product. (Alternatively, you can add an API product to an existing key.)

        Note: You must include all current attribute, API product, and callback
        values in the payload along with any changes you want to make;
        otherwise, the existing values are removed. To display the current
        values, get the developer app profile. You cannot update the scopes
        associated with the app by using this API. Instead, use Update app scope
        API.

        Apigee Edge for Public Cloud only: OAuth access tokens and Key
        Management Service (KMS) entities (apps, developers, and API products)
        are cached for 180 seconds (current default). Any custom attributes
        associated with these entities also get cached for at least 180 seconds
        after the entity is accessed at runtime. Therefore, an ExpiresIn element
        on the OAuthV2 policy won't be able to expire an access token in less
        than 180 seconds.
        """

        resource = f"/developers/{self.email}/apps/{app_name}"
        url = f"{self.client.base_url}{resource}"
        resp = self.client.put(url=url, json=body)
        if resp.status_code != 200:
            raise Exception(
                f"PUT request to {resp.url} failed with status_code: {resp.status_code}, Reason: {resp.reason} and Content: {resp.text}"
            )
        return resp.json()

    def delete_app_by_name(self, app_name: str) -> None:
        """
        Deletes a developer app.

        With Apigee Edge for Public Cloud, deletion of the developer app and
        associated artifacts happens asynchronously. The developer app is
        deleted immediately, but the resources associated with that developer
        app, such as app keys or access tokens, may take anywhere from a few
        seconds to a few minutes to be automatically deleted.
        """

        resource = f"/developers/{self.email}/apps/{app_name}"
        url = f"{self.client.base_url}{resource}"
        resp = self.client.delete(url=url)
        if resp.status_code != 200:
            raise Exception(
                f"GET request to {resp.url} failed with status_code: {resp.status_code}, Reason: {resp.reason} and Content: {resp.text}"
            )
        return resp.json()

    def get_app_attributes(self, app_name) -> "dict":
        """Gets developer app attributes and their values."""

        resource = f"/developers/{self.email}/apps/{app_name}/attributes"
        url = f"{self.client.base_url}{resource}"
        resp = self.client.get(url=url)
        if resp.status_code != 200:
            raise Exception(
                f"GET request to {resp.url} failed with status_code: {resp.status_code}, Reason: {resp.reason} and Content: {resp.text}"
            )
        return resp.json()

    def post_app_attributes(self, app_name: str, body: dict) -> "dict":
        """
        Updates app attributes.

        This API replaces the current list of attributes with the attributes
        specified in the request body. This lets you update existing attributes,
        add new attributes, or delete existing attributes by omitting them from
        the request body.

        Apigee Edge for Public Cloud only: OAuth access tokens and Key
        Management Service (KMS) entities (apps, developers, and API products)
        are cached for 180 seconds (current default). Any custom attributes
        associated with these entities also get cached for at least 180 seconds
        after the entity is accessed at runtime. Therefore, an ExpiresIn element
        on the OAuthV2 policy won't be able to expire an access token in less
        than 180 seconds.
        """

        resource = f"/developers/{self.email}/apps/{app_name}/attributes"
        url = f"{self.client.base_url}{resource}"
        resp = self.client.post(url=url, json=body)
        if resp.status_code != 200:
            raise Exception(
                f"POST request to {resp.url} failed with status_code: {resp.status_code}, Reason: {resp.reason} and Content: {resp.text}"
            )
        return resp.json()

    def get_app_attribute_by_name(self, app_name: str, attribute_name: str) -> "dict":
        """Gets a developer app attribute"""

        resource = f"/developers/{self.email}/apps/{app_name}/attributes/{attribute_name}"
        url = f"{self.client.base_url}{resource}"
        resp = self.client.get(url=url)
        if resp.status_code != 200:
            raise Exception(
                f"GET request to {resp.url} failed with status_code: {resp.status_code}, Reason: {resp.reason} and Content: {resp.text}"
            )
        return resp.json()

    def post_app_attribute_by_name(self, app_name: str, attribute_name: str, body: dict) -> "dict":
        """
        Updates a developer app attribute.

        Apigee Edge for Public Cloud only: OAuth access tokens and Key
        Management Service (KMS) entities (apps, developers, and API products)
        are cached for 180 seconds (current default). Any custom attributes
        associated with these entities also get cached for at least 180 seconds
        after the entity is accessed at runtime. Therefore, an ExpiresIn element
        on the OAuthV2 policy won't be able to expire an access token in less
        than 180 seconds.
        """

        resource = f"/developers/{self.email}/apps/{app_name}/attributes/{attribute_name}"
        url = f"{self.client.base_url}{resource}"
        resp = self.client.post(url=url, json=body)
        if resp.status_code != 200:
            raise Exception(
                f"POST request to {resp.url} failed with status_code: {resp.status_code}, Reason: {resp.reason} and Content: {resp.text}"
            )
        return resp.json()

    def delete_app_attribute_by_name(self, app_name: str, attribute_name: str) -> "dict":
        """Deletes a developer app attribute"""

        resource = f"/developers/{self.email}/apps/{app_name}/attributes/{attribute_name}"
        url = f"{self.client.base_url}{resource}"
        resp = self.client.delete(url=url)
        if resp.status_code != 200:
            raise Exception(
                f"DELETE request to {resp.url} failed with status_code: {resp.status_code}, Reason: {resp.reason} and Content: {resp.text}"
            )
        return resp.json()


class ApiProductsAPI:
    """
    An API product consists of a list of API resources (URIs) and custom
    metadata required by the API provider. API products enable you to bundle and
    distribute your APIs to multiple developer groups simultaneously without
    having to modify code. API products provide the basis for access control in
    Apigee, as they provide control over the set of API resources that apps are
    allowed to consume. As part of the app provisioning workflow, developers
    select from a list of API products. This selection of an API product is
    usually made in the context of a developer portal. The developer app is
    provisioned with a key and secret (generated by and stored on Apigee Edge)
    that enable the app to access the URIs bundled in the selected API product.
    To access API resources bundled in an API product, the app must present the
    API key issued by Apigee Edge. Apigee Edge will resolve the key that is
    presented against an API product, and then check associated API resources
    and quota settings. The API supports multiple API products per app key,
    which enables app developers to consume multiple API products without
    requiring multiple keys. Also, a key can be 'promoted' from one API product
    to another. This enables you to promote developers from 'free' to 'premium'
    API products seamlessly and without user interruption.
    """

    def __init__(self, client: RestClient) -> None:
        self.client = client

    def get_products(self, **query_params) -> "dict":
        """
        Lists API products for an organization. Filter the list by passing an
        attributename and attibutevalue. With Apigee Edge for Public Cloud:

        The limit on the number of API products returned is 1000. Paginate the
        list of API products returned using the startKey and count query
        parameters.
        """
        resource = f"/apiproducts"
        url = f"{self.client.base_url}{resource}"
        resp = self.client.get(url=url, params=query_params)
        if resp.status_code != 200:
            raise Exception(
                f"GET request to {resp.url} failed with status_code: {resp.status_code}, Reason: {resp.reason} and Content: {resp.text}"
            )
        return resp.json()

    def post_products(self, body: dict) -> "dict":
        """
        Creates an API product in an organization. You create API products after
        you have proxied backend services using API proxies.

        An API product is a collection of API resources combined with quota
        settings and metadata that you can use to deliver customized and
        productized API bundles to your developer community. This metadata may
        include the scope, environments, API proxies, and extensible profile.

        API products enable you to repackage APIs on-the-fly, without having to
        do any additional coding or configuration.

        Apigee recommends that you start with a simple API product including
        only required elements. Then provision credentials to apps to enable
        them to start testing your APIs. Once you have authentication and
        authorization working against a simple API product, you can iterate to
        create finer-grained API products, defining different sets of API
        resources for each API product.

        Warning:

        If you don't specify an API proxy in the request body, any app
        associated with the API product can make calls to any API in your entire
        organization. If you don't specify an environment in the request body,
        the API product allows access to all environments. For more information,
        see Manage API products. Ensure optimal API product and app security

        An organization-level property,
        features.keymanagement.disable.unbounded.permissions, strengthens the
        security of API products in verifying API calls. When the property is
        set to true, the following features are enforced.

        App creation: When creating a developer or company app, the Edge API
        requires that the app be associated with an API product. (The Edge UI
        already enforces this.)

        API product configuration: To create or update an API product, the API
        product must include at least one API proxy or a resource path in its
        definition.

        Runtime security: API calls are rejected by an API product in the
        following situations:

        An API product doesn't include at least one API proxy or resource path.

        If the flow.resource.name variable in the message doesn't include a
        resource path that the API product can evaluate.

        If the app making the API call isn't associated with an API product.

        Note: Setting this organization property requires system administrator
        privileges. Edge for Private Cloud system administrators can add this
        property when updating organization properties. If you are an Edge for
        Public Cloud user, contact Apigee Support to set the organization
        property.
        """
        resource = f"/apiproducts"
        url = f"{self.client.base_url}{resource}"
        resp = self.client.post(url=url, json=body)
        if resp.status_code != 201:
            raise Exception(
                f"POST request to {resp.url} failed with status_code: {resp.status_code}, Reason: {resp.reason} and Content: {resp.text}"
            )
        return resp.json()

    def get_product_by_name(self, product_name: str, **query_params) -> "dict":
        """
        Gets configuration details for an API product.

        The API product name required in the request URL is the internal name of
        the product, not the display name. While they may be the same, it
        depends on whether the API product was created via the UI or API. View
        the list of API products to verify the internal name.

        With Apigee Edge for Public Cloud:

        The limit on the number of entities returned is 100. Paginate the list
        of API products returned using the startkey and count query parameters.
        """
        resource = f"/apiproducts/{product_name}"
        url = f"{self.client.base_url}{resource}"
        resp = self.client.get(url=url, params=query_params)
        if resp.status_code != 200:
            raise Exception(
                f"GET request to {resp.url} failed with status_code: {resp.status_code}, Reason: {resp.reason} and Content: {resp.text}"
            )
        return resp.json()

    def put_product_by_name(self, product_name: str, body: dict) -> "dict":
        """
        Updates an existing API product.

        Note: You must include all required values, whether or not you are
        updating them, as well as any optional values that you are updating.

        The API product name required in the request URL is the internal name of
        the product, not the display name. While they may be the same, it
        depends on whether the API product was created via UI or API. View the
        list of API products to verify the internal name.

        Apigee Edge for Public Cloud only: OAuth access tokens and Key
        Management Service (KMS) entities (apps, developers, and API products)
        are cached for 180 seconds (current default). Any custom attributes
        associated with these entities also get cached for at least 180 seconds
        after the entity is accessed at runtime. Therefore, an ExpiresIn element
        on the OAuthV2 policy won't be able to expire an access token in less
        than 180 seconds.
        """
        resource = f"/apiproducts/{product_name}"
        url = f"{self.client.base_url}{resource}"
        resp = self.client.put(url=url, json=body)
        if resp.status_code != 200:
            raise Exception(
                f"PUT request to {resp.url} failed with status_code: {resp.status_code}, Reason: {resp.reason} and Content: {resp.text}"
            )
        return resp.json()

    def delete_product_by_name(self, product_name: str) -> "dict":
        """
        Deletes an API product from an organization.

        Deleting an API product will cause app requests to the resource URIs
        defined in the API product to fail. Ensure that you create a new API
        product to serve existing apps, unless your intention is to disable
        access to the resources defined in the API product.

        The API product name required in the request URL is the internal name of
        the product, not the display name. While they may be the same, it
        depends on whether the API product was created via the UI or API. View
        the list of API products to verify the internal name.
        """
        resource = f"/apiproducts/{product_name}"
        url = f"{self.client.base_url}{resource}"
        resp = self.client.delete(url=url)
        if resp.status_code != 200:
            raise Exception(
                f"DELETE request to {resp.url} failed with status_code: {resp.status_code}, Reason: {resp.reason} and Content: {resp.text}"
            )
        return resp.json()

    def get_product_attributes(self, product_name: str) -> "dict":
        """Lists all API product attributes"""
        resource = f"/apiproducts/{product_name}/attributes"
        url = f"{self.client.base_url}{resource}"
        resp = self.client.get(url=url)
        if resp.status_code != 200:
            raise Exception(
                f"GET request to {resp.url} failed with status_code: {resp.status_code}, Reason: {resp.reason} and Content: {resp.text}"
            )
        return resp.json()

    def post_product_attributest(self, product_name: str, body: dict) -> "dict":
        """
        Updates or creates API product attributes. This API replaces the current
        list of attributes with the attributes specified in the request body. In
        this way, you can update existing attributes, add new attributes, or
        delete existing attributes by omitting them from the request body.

        Apigee Edge for Public Cloud only: OAuth access tokens and Key
        Management Service (KMS) entities (apps, developers, and API products)
        are cached for 180 seconds (current default). Any custom attributes
        associated with these entities also get cached for at least 180 seconds
        after the entity is accessed at runtime. Therefore, an ExpiresIn element
        on the OAuthV2 policy won't be able to expire an access token in less
        than 180 seconds.
        """
        resource = f"/apiproducts/{product_name}/attributes"
        url = f"{self.client.base_url}{resource}"
        resp = self.client.post(url=url, json=body)
        if resp.status_code != 200:
            raise Exception(
                f"POST request to {resp.url} failed with status_code: {resp.status_code}, Reason: {resp.reason} and Content: {resp.text}"
            )
        return resp.json()

    def get_product_attribute_by_name(self, product_name: str, attribute_name: str) -> "dict":
        """Gets the value of an API product attribute."""
        resource = f"/apiproducts/{product_name}/attributes/{attribute_name}"
        url = f"{self.client.base_url}{resource}"
        resp = self.client.get(url=url)
        if resp.status_code != 200:
            raise Exception(
                f"GET request to {resp.url} failed with status_code: {resp.status_code}, Reason: {resp.reason} and Content: {resp.text}"
            )
        return resp.json()

    def post_product_attribute_by_name(self, product_name: str, attribute_name: str, body: dict) -> "dict":
        """
        Updates the value of an API product attribute.

        Apigee Edge for Public Cloud only: OAuth access tokens and Key
        Management Service (KMS) entities (apps, developers, and API products)
        are cached for 180 seconds (current default). Any custom attributes
        associated with these entities also get cached for at least 180 seconds
        after the entity is accessed at runtime. Therefore, an ExpiresIn element
        on the OAuthV2 policy won't be able to expire an access token in less
        than 180 seconds.
        """
        resource = f"/apiproducts/{product_name}/attributes/{attribute_name}"
        url = f"{self.client.base_url}{resource}"
        resp = self.client.post(url=url, json=body)
        if resp.status_code != 200:
            raise Exception(
                f"POST request to {resp.url} failed with status_code: {resp.status_code}, Reason: {resp.reason} and Content: {resp.text}"
            )
        return resp.json()

    def delete_product_attribute_by_name(self, product_name: str, attribute_name: str) -> "dict":
        """Deletes an API product attribute"""
        resource = f"/apiproducts/{product_name}/attributes/{attribute_name}"
        url = f"{self.client.base_url}{resource}"
        resp = self.client.delete(url=url)
        if resp.status_code != 200:
            raise Exception(
                f"DELETE request to {resp.url} failed with status_code: {resp.status_code}, Reason: {resp.reason} and Content: {resp.text}"
            )
        return resp.json()


class DebugSessionsAPI:
    """
    Create debug sessions in Apigee Edge to record specified messages and
    associated pipeline processing metadata for debugging purposes
    """

    def __init__(self, env_name: str, api_name: str, revision_number: str, client: RestClient) -> None:
        self.client = client
        self.env_name = env_name
        self.api_name = api_name
        self.revision_number = revision_number

    def get_debugsessions(self):
        """
        Lists debug sessions that were created either by using the Create
        debug session API or the Trace tool in the Edge UI
        """
        resource = f"/environments/{self.env_name}/apis/{self.api_name}/revisions/{self.revision_number}/debugsessions"
        url = f"{self.client.base_url}{resource}"
        resp = self.client.get(url=url)
        if resp.status_code != 200:
            raise Exception(
                f"GET request to {resp.url} failed with status_code: {resp.status_code}, Reason: {resp.reason} and Content: {resp.text}"
            )
        return resp.json()

    def post_debugsession(self, body: dict, **query_params):
        """
        Creates a debug session.

        A debug session records detailed information on messages, flow
        processing, and policy execution during processing by an API proxy.

        The data returned in the debug session is a single XML or JSON
        representation of all debug data for each message exchange. The debug
        data is the same as that used to generate the Trace view in the Edge UI.

        A debug session captures a maximum of 20 messages or records for a
        maximum of 10 minutes (by default), whichever comes first.

        Debugging involves the following steps:

        Start a debug session by creating a debug session. Send a message for
        that deployed API proxy. Retrieve the debug data associated with the
        debug session. The data can be fetched by issuing a GET call on the
        session. Close the debug session. (Closing the debug session discards
        all the associated data). When creating a debug session, you can set a
        filter that captures only API calls with specific query parameters
        and/or HTTP headers. Filtering is particularly useful for
        troubleshooting.

        For example, if you wanted to capture only API calls with an Accept:
        application/json header, you'd create a debug session with that filter.
        Filtering API calls in a debug session is particularly useful for
        root-case analysis to target specific calls that may be causing
        problems.

        The filter is set using by appending the filter details as a query
        parameter to the API call. The query parameters begin with either
        header_ or qparam_ to indicate a header or query parameter. For example:

        header_name=value: Captures only calls that contain the specific header
        and value. Header name and value must be URL encoded. For example:
        header_Accept=application%2Fjson

        qparam_name=value: Captures only calls that contain the specific query
        parameter and value. Query parameter name and value must be URL encoded.
        For example: qparam_user=john%20doe

        If you use multiple headers and/or query parameters in the filter, all
        conditions must be met in order for API call to be captured. Here's how
        the previous two examples would be combined into a single filter:

        header_Accept=application%2Fjson&qparam_user=john%20doe

        The filter query parameters are combined with the query parameters you
        set in the fields below.
        """
        resource = f"/environments/{self.env_name}/apis/{self.api_name}/revisions/{self.revision_number}/debugsessions"
        url = f"{self.client.base_url}{resource}"
        resp = self.client.post(url=url, params=query_params, json=body)
        if resp.status_code != 201:
            raise Exception(
                f"POST request to {resp.url} failed with status_code: {resp.status_code}, Reason: {resp.reason} and Content: {resp.text}"
            )
        return resp.json()

    def delete_debugsession_by_name(self, session_name: str):
        """Deletes a debug session."""
        resource = f"/environments/{self.env_name}/apis/{self.api_name}/revisions/{self.revision_number}/debugsessions/{session_name}"
        url = f"{self.client.base_url}{resource}"
        resp = self.client.delete(url=url)
        if resp.status_code != 200:
            raise Exception(
                f"DELETE request to {resp.url} failed with status_code: {resp.status_code}, Reason: {resp.reason} and Content: {resp.text}"
            )
        return resp.json()

    def get_transaction_data(self, session_name: str):
        """
        Gets transaction IDs for a debug session that was created either by
        using the Create debug session API or the Trace tool in the Edge UI.

        Each item in the returned list is the unique ID for a debug session
        transaction associated with a single request to the API proxy specified.

        Use the Get debug session transaction data API to retrieve the raw debug
        data for the transaction.
        """
        resource = f"/environments/{self.env_name}/apis/{self.api_name}/revisions/{self.revision_number}/debugsessions/{session_name}/data"
        url = f"{self.client.base_url}{resource}"
        resp = self.client.get(url=url)
        if resp.status_code != 200:
            raise Exception(
                f"GET request to {resp.url} failed with status_code: {resp.status_code}, Reason: {resp.reason} and Content: {resp.text}"
            )
        return resp.json()

    def get_transaction_data_by_id(self, session_name: str, transaction_id: str):
        """
        Gets debug session transaction data. To get a list of transaction IDs,
        see Get debug session transaction IDs.

        The debug data returned by this APl is the same debug data that populates the
        Trace tool in the Edge management UI. For more information on the Trace tool,
        see Using the Trace tool.
        """
        resource = f"/environments/{self.env_name}/apis/{self.api_name}/revisions/{self.revision_number}/debugsessions/{session_name}/data/{transaction_id}"
        url = f"{self.client.base_url}{resource}"
        resp = self.client.get(url=url)
        if resp.status_code != 200:
            raise Exception(
                f"GET request to {resp.url} failed with status_code: {resp.status_code}, Reason: {resp.reason} and Content: {resp.text}"
            )
        return resp.json()


class DeploymentsAPI:
    """Manage API proxy and shared flow deployments."""

    def __init__(self, client: RestClient) -> None:
        self.client = client

    def get_deployments(self):
        pass

    def get_deployments_by_apiname(self):
        pass

    def get_deployments_by_revision(self):
        pass

    def post_deployments_by_revision(self):
        pass


class UserRolesAPI:
    def __init__(self, client: RestClient) -> None:
        self.client = client


class AppKeysAPI:
    """
    Manage consumer credentials for apps associated with individual developers.

    Credential pairs consisting of consumer key and consumer secret are
    provisioned by Apigee Edge to apps for specific API products. Apigee Edge
    maintains the relationship between consumer keys and API products, enabling
    API products to be added to and removed from consumer keys. A single
    consumer key can be used to access multiple API products. Keys may be
    manually or automatically approved for API products--how they are issued
    depends on the API product configuration. A key must approved and approved
    for an API product to be capable of accessing any of the URIs defined in the
    API product.
    """

    def __init__(self, client: RestClient) -> None:
        self.client = client


class AccessTokensAPI:
    """
    Apigee Edge uses access tokens to define a user's permissions for modifying
    and using a specific API. When you apply OAuth 2.0 to the API, Edge checks
    the request for an access token. If an access token is present, and the API
    is within the scope of the access token, you are allowed to access the API.
    Prerequisites to use this API call are:

    The API provider has created an organization. You are a registered
    developer. You have created an app. You have a valid consumer key. An access
    token has been generated.
    """

    def __init__(self, client: RestClient) -> None:
        self.client = client


class UsersAPI:
    def __init__(self, client: RestClient) -> None:
        self.client = client


class AuthorizationCodesAPI:
    def __init__(self, client: RestClient) -> None:
        self.client = client


class RefreshTokensAPI:
    def __init__(self, client: RestClient) -> None:
        self.client = client


class OrganizationsAPI:
    def __init__(self, client: RestClient) -> None:
        self.client = client


class KVMAPI:
    def __init__(self, client: RestClient) -> None:
        self.client = client


class KeystoreTrustoreAPI:
    def __init__(self, client: RestClient) -> None:
        self.client = client
