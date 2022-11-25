"""
This is a self contain wraper for a bunch of authentication methods in APIM. NOT
ONLY the identity service is taking into account in here, you will also find
authenticators for keycloack and more... so feel free to keep adding
authenticators here and maybe move this file to its own library.
"""

import uuid
from time import time
from typing import Literal

import jwt
from pydantic import BaseModel, HttpUrl, validator
from abc import ABC, abstractmethod
from typing import Literal
from urllib.parse import parse_qs, urlparse

import requests
from lxml import html


class ApigeeConfig(BaseModel):
    """Basic Apigee config"""

    environment: Literal[
        "internal-dev",
        "internal-qa",
        "internal-dev-sandbox",
        "internal-qa-sandbox",
        "ref",
        "int",
        "prod",
    ] = "internal-dev"
    org: Literal["nhsd-nonprod", "nhsd-prod"] = "nhsd-nonprod"

    @property
    def identity_service_base_url(self):
        prefix = "https://"
        host = "api.service.nhs.uk"
        path = "/oauth2-mock"  # lets just support mock auth v2...
        if self.environment != "prod":
            prefix += f"{self.environment}."
        return f"{prefix}{host}{path}"


class KeycloakConfig(BaseModel):
    """Basic Keycloak config"""

    realm: Literal[
        "Cis2-mock-internal-dev",
        "Cis2-mock-internal-qa",
        "Cis2-mock-sandbox",
        "Cis2-mock-int",
        "NHS-Login-mock-internal-dev",
        "NHS-Login-mock-internal-qa",
        "NHS-Login-mock-sandbox",
        "NHS-Login-mock-int",
        "Api-producers",  # just in case u want to get a cheeky token for proxygen ;)
    ]

    @property
    def keycloak_url(self):
        prefix = "https://"
        host = "identity.ptl.api.platform.nhs.uk"
        path = f"/auth/realms/{self.realm}/protocol/openid-connect"
        return f"{prefix}{host}{path}"


class KeycloakUserConfig(KeycloakConfig):
    client_id: str
    client_secret: str
    redirect_uri: HttpUrl = "https://example.org"
    login_form: dict


class AuthorizationCodeConfig(ApigeeConfig):
    """Config needed to authenticate using authorizaztion_code flow in the identity service"""

    callback_url: HttpUrl
    auth_url: HttpUrl = f"{ApigeeConfig.identity_service_base_url}/authorize"
    token_url: HttpUrl = f"{ApigeeConfig.identity_service_base_url}/token"
    client_id: str
    client_secret: str
    scope: Literal["nhs-login", "nhs-cis2"]
    login_form: dict

    @validator("environment")
    # The dream is to suport all the auth methods in all the environments
    # however this is only true for client_credentials at the time of writing
    # this library, we dont have at the moment a complete map between identity
    # service deployment environments and keycloak realms so authorization_code
    # and token_exchange are only supported in internal-dev, internal-qa and
    # int. We use validators to handle this and when the moment comes we can
    # just delete them.
    def validate_environment(cls, environment):
        if environment in [
            "internal-dev-sandbox",
            "internal-qa-sandbox",
            "sandbox",
            "ref",
            "prod",
        ]:
            raise ValueError(
                f"This is awkward.. we dont support auth_code flow for the {environment} just yet"
            )
        return environment


class ClientCredentialsConfig(ApigeeConfig):
    """Config needed to authenticate using client_credentials flow in the identity service"""

    client_id: str
    jwt_private_key: str
    jwt_kid: str

    def encode_jwt(self):
        url = f"{self.identity_service_base_url}/token"
        claims = {
            "sub": self.client_id,
            "iss": self.client_id,
            "jti": str(uuid.uuid4()),
            "aud": url,
            "exp": int(time()) + 300,  # 5 minutes in the future
        }
        additional_headers = {"kid": self.jwt_kid}
        client_assertion = jwt.encode(
            claims, self.jwt_private_key, algorithm="RS512", headers=additional_headers
        )
        return client_assertion


class TokenExchangeConfig(ClientCredentialsConfig):
    id_token: str


# TODO
class KeycloakSignedJWTConfig:
    pass


class NHSLoginConfig:
    pass


class BananaAuthenticatorConfig:  # Placeholder
    pass


class Authenticator(ABC):
    """Defines the interface"""

    @abstractmethod
    def get_token(self):
        pass


class ClientCredentialsAuthenticator(Authenticator):
    """
    Gets you authenticated using the client_credentials flow in the apim
    identity service, this method of authentication is also known as
    'application restricted' or 'machine user' or 'signed jwt', you can read
    how this pattern works here:
    https://digital.nhs.uk/developer/guides-and-documentation/security-and-authorisation/application-restricted-restful-apis-signed-jwt-authentication
    """

    def __init__(self, config=ClientCredentialsConfig) -> None:
        self.config = config

    def get_token(self):
        login_session = requests.session()
        data = {
            "grant_type": "client_credentials",
            "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
            "client_assertion": self.config.encode_jwt(),
        }
        # 1. Do the post call to the identity service
        url = f"{self.config.identity_service_base_url}/token"
        resp = login_session.post(url, data=data)
        # 2. Catch any unexpected error
        if resp.status_code != 200:
            raise RuntimeError(f"{resp.status_code}: {resp.text}")
        # 3. Return your sweet sweet profit
        return resp.json()


class AuthorizationCodeAuthenticator(Authenticator):
    """
    Complete the user-restricted authentication journey for CIS2 or NHS-LOGIN using
    our auth endpoint.

    This webpage does a pretty good job of explaining the journey:
    https://digital.nhs.uk/developer/guides-and-documentation/security-and-authorisation/user-restricted-restful-apis-nhs-cis2-combined-authentication-and-authorisation
    """

    def __init__(self, config=AuthorizationCodeConfig):
        self.config = config

    @staticmethod
    def _get_authorize_endpoint_response(
        session: requests.Session,
        identity_service_base_url,
        client_id,
        callback_url,
        auth_scope: Literal["nhs-login", "nhs-cis2"],
    ):
        authorize_url = f"{identity_service_base_url}/authorize"
        resp = session.get(
            authorize_url,
            params={
                "client_id": client_id,
                "redirect_uri": callback_url,
                "response_type": "code",
                "scope": auth_scope,
                "state": "1234567890",
            },
        )
        if resp.status_code != 200:
            raise RuntimeError(
                f"{authorize_url} request returned {resp.status_code}: {resp.text}"
            )
        return resp

    @staticmethod
    def _get_authorize_form_submission_data(authorize_form, login_options):
        inputs = list(authorize_form.inputs)

        form_submission_data = {}
        # This loop picks up the pre-populated defaults, which is
        # sufficient for simulated auth. Defaults can be appended to with
        # the "login_options".
        for _input in inputs:
            input_data = dict(_input.items())
            name = input_data["name"]
            value = input_data["value"]
            form_submission_data[name] = value

        form_submission_data.update(login_options)
        return form_submission_data

    @staticmethod
    def _get_authorization_form(html_str):
        tree = html.fromstring(html_str)
        form = tree.forms[0]
        return form

    @staticmethod
    def _log_in_identity_service_provider(
        session: requests.Session,
        authorize_response,
        authorize_form,
        form_submission_data,
    ):
        form_submit_url = authorize_form.action or authorize_response.request.url
        resp = session.request(
            authorize_form.method, form_submit_url, data=form_submission_data
        )
        # TODO: Investigate why when using the fixtures it returns 404 and when
        # using with external credentials returns 200
        # if resp.status_code != 200:
        #     raise RuntimeError(
        #         f"{form_submit_url} request returned {resp.status_code}: {resp.text}"
        #     )
        return resp

    @staticmethod
    def _get_auth_code_from_mock_auth(response_identity_service_login):
        qs = urlparse(
            response_identity_service_login.history[-1].headers["Location"]
        ).query
        auth_code = parse_qs(qs)["code"]
        if isinstance(auth_code, list):
            # in case there's multiple, this was a bug at one stage
            auth_code = auth_code[0]

        return auth_code

    def get_token(self):
        login_session = requests.session()

        # 1. Hit `authorize` endpoint w/ required query params --> we
        # are redirected to the simulated_auth page. The requests package
        # follows those redirects.
        authorize_response = self._get_authorize_endpoint_response(
            login_session,
            self.config.identity_service_base_url,
            self.config.client_id,
            self.config.callback_url,
            self.config.scope,
        )

        authorize_form = self._get_authorization_form(
            authorize_response.content.decode()
        )
        # 2. Parse the login page.  For keycloak this presents an
        # HTML form, which must be filled in with valid data.  The tester
        # can submits their login data with the `login_form` field.

        form_submission_data = self._get_authorize_form_submission_data(
            authorize_form, self.config.login_form
        )

        # form_submission_data["username"] = 656005750104
        #     # And here we inject a valid mock username for keycloak.
        #     # For reference some valid cis2 mock usernames are...
        #     # 656005750104 	surekha.kommareddy@nhs.net
        #     # 656005750105 	darren.mcdrew@nhs.net
        #     # 656005750106 	riley.jones@nhs.net
        #     # 656005750107 	shirley.bryne@nhs.net

        #     # And some valid nhs-login mock usernames are...
        #     # 9912003071      for High - P9
        #     # 9912003072      for Medium - P5
        #     # 9912003073      for Low - P0

        # 3. POST the filled in form. This is equivalent to clicking the
        # "Login" button if we were a human.

        response_identity_service_login = self._log_in_identity_service_provider(
            login_session, authorize_response, authorize_form, form_submission_data
        )
        # 4. The mock auth redirected us back to the
        # identity-service, which redirected us to whatever our app's
        # callback-url was set to.  We don't actually care about the
        # content our callback-url page, we just need the auth_code that
        # was provided in the redirect.
        auth_code = self._get_auth_code_from_mock_auth(response_identity_service_login)

        # 5. Finally, get an access token.
        resp = login_session.post(
            f"{self.config.identity_service_base_url}/token",
            data={
                "grant_type": "authorization_code",
                "code": auth_code,
                "redirect_uri": self.config.callback_url,
                "client_id": self.config.client_id,
                "client_secret": self.config.client_secret,
            },
        )
        resp.raise_for_status()

        # 6. Profit.. sweet sweet profit.
        return resp.json()


class KeycloakUserAuthenticator(Authenticator):
    """
    This is the first step is User Restricted Separate Auth a.k.a Token
    Exchange.  We get a set of tokens from our mock version of CIS2/NHS-LOGIN.
    The reponse includes an ID token, which we will then pass to identity
    service.  Identity service validates the ID *token*, and *exchanges* is it
    for an access token for the NHSD APIM proxies (which probably includes the
    proxy under test).

    It is important to know that for nhs-login we are using client-id and secret
    as supposed to be using signed jwt for authentication as described in the
    documentation. This is so we can use this function to authenticate against
    both providers and at the end of the day the token response from keycloak
    will be the same regardless the authentication method.

    Now if you feel you want to introduce signed-jwt authentication for keycloak
    by all means go for it, hopefully you will find it as easy as implementing a
    new authenticator class...
    """

    def __init__(self, config=KeycloakUserConfig) -> None:
        self.config = config

    def get_token(self):

        login_session = requests.session()
        # 1. Get me that auth page
        resp = login_session.get(
            f"{self.config.keycloak_url}/auth",
            params={
                "response_type": "code",
                "client_id": self.config.client_id,
                "scope": "openid",
                "redirect_uri": self.config.redirect_uri,
            },
        )
        # 2. Parse it!
        tree = html.fromstring(resp.text)
        form = tree.get_element_by_id("kc-form-login")
        # 3. Complete the login form with the credentials in login_form.
        resp2 = login_session.post(form.action, data=self.config.login_form)
        location = urlparse(resp2.history[-1].headers["location"])
        params = parse_qs(location.query)
        # 4. Get me that sweet code from the redirect_uri so I can get my token
        code = params["code"]
        # 5. Get the token
        resp3 = login_session.post(
            f"{self.config.keycloak_url}/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": self.config.client_id,
                "client_secret": self.config.client_secret,
                "redirect_uri": self.config.redirect_uri,
            },
        )
        # 6. Return your deserved profit.
        return resp3.json()


class TokenExcchangeAuthenticator(Authenticator):
    """
    Get u authenticated using the token_exchange flow in identity service
    """

    def __init__(self, config=TokenExchangeConfig) -> None:
        self.config = config

    # At this point you will be asking yourself 'why we dont dont just implement
    # the hole token exchange flow inside this class?' my answer to that is that
    # I would love every api-producer to understand this flow in detail (you can
    # call me a dreamer) and I believe that forcing them to get a token against
    # Keycloak first and then passing the id_token here makes the hole thing
    # ridiculously explicit. Also how knows... maybe this library will be
    # implemented in some production system one day.
    def get_token(self):
        data = {
            "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
            "subject_token_type": "urn:ietf:params:oauth:token-type:id_token",
            "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
            "subject_token": self.config.id_token,
            "client_assertion": self.config.encode_jwt(),
        }
        # 1. Make the post request to the identity service
        url = f"{self.config.identity_service_base_url}/token"
        resp = requests.post(url, data=data)
        # 2. Catch any error
        if resp.status_code != 200:
            raise RuntimeError(f"{resp.status_code}: {resp.text}")
        # 3. Return your profit
        return resp.json()


# TODO:
class KeycloakSignedJWTAuthenticator(Authenticator):
    """Authenticates you against keycloak using signed jwt"""

    def __init__(self, config=KeycloakSignedJWTConfig) -> None:
        self.config = config
        raise NotImplemented(f"TODO")

    def get_token(self):
        raise NotImplemented(f"TODO")


class NHSLoginSandpitAuthenticator(Authenticator):
    """Authenticates you against NHS-Login sandpit environment"""

    def __init__(self, config=NHSLoginConfig) -> None:
        self.config = config
        raise NotImplemented(f"TODO")

    def get_token(self):
        raise NotImplemented(f"TODO")


class NHSLoginAosAuthenticator(Authenticator):
    """Authenticates you against NHS-Login aos environment"""

    def __init__(self, config=NHSLoginConfig) -> None:
        self.config = config
        raise NotImplemented(f"TODO")

    def get_token(self):
        raise NotImplemented(f"TODO")


class NHSLoginProdAuthenticator(Authenticator):
    """Authenticates you against NHS-Login prod environment"""

    def __init__(self, config=NHSLoginConfig) -> None:
        self.config = config
        raise NotImplemented(f"TODO")

    def get_token(self):
        raise NotImplemented(f"TODO")


class BananaAuthenticator(Authenticator):  # Placeholder
    """Authenticates you against a banana"""

    def __init__(self, config=BananaAuthenticatorConfig) -> None:
        self.config = config
        raise NotImplemented(f"TODO")

    def get_token(self):
        raise NotImplemented(f"TODO")
