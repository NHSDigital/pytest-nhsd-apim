from warnings import warn
from typing import Literal, Union, Dict, Any

import pytest
from typing_extensions import Annotated
from pydantic import BaseModel, Field, validator

from .log import log, log_method


class BaseAuthorization(BaseModel):
    api_name: str
    generation: Literal[1, 2] = 2

    def dict(self, **kwargs):
        """
        Construct the product scope when we export the Authorization
        subclasses.
        """
        # Yeah this breaks the inheritance encapsulation
        # slightly... but I'm tired.

        d = super().dict(**kwargs)
        access = d["access"]
        level = d["level"]
        ACCESS_SCOPE_PARTS = {
            "healthcare_worker": "user-nhs-cis2",
            "patient": "user-nhs-login",
            "application": "app",
        }
        scope = ":".join(
            ["urn:nhsd:apim", ACCESS_SCOPE_PARTS[access], level, self.api_name]
        )
        if access == "application" and level == "level0":
            scope = None
        d["scope"] = scope
        return d


class UserRestrictedAuthorization(BaseAuthorization):
    authentication: Literal["combined", "separate"] = "combined"
    login_form: Dict[str, Any] = Field(default_factory=dict)


class HealthcareWorkerAuthorization(UserRestrictedAuthorization):
    """
    Uses CIS2 as the identity provider
    """

    access: Literal["healthcare_worker"]
    level: Literal["aal1", "aal3"]

    @validator("generation")
    def warn_generation_1_deprecated(cls, generation):
        if generation == 1:
            warn("Generation 1 auth is deprecated for healthcare_worker access.")
        return generation


class PatientAuthorization(UserRestrictedAuthorization):
    """
    Uses NHSLogin as the identity provider
    """

    access: Literal["patient"]
    level: Literal["P0", "P5", "P9"]
    generation: Literal[1] = 1


class ApplicationAuthorization(BaseAuthorization):
    access: Literal["application"]
    level: Literal["level0", "level3"]


class Authorization(BaseModel):
    nhsd_apim_authorization: Annotated[
        Union[
            HealthcareWorkerAuthorization,
            PatientAuthorization,
            ApplicationAuthorization,
        ],
        Field(discriminator="access"),
    ]


@pytest.fixture()
@log_method
def nhsd_apim_authorization(request):
    """
    Mark your test with a `nhsd_apim_authorization marker`.
    The call the `nhsd_apim_auth_headers` fixture to access your proxy.

    >>> import pytest
    >>> import requests
    >>> @pytest.mark.nhsd_apim_authorization(api_name="mock-jwks", access='healthcare_worker', level="aal3")
    >>> def test_application_restricted_access(proxy_url, nhsd_apim_auth_header):
    >>>     resp = requests.get(proxy_url + "/a/path/that/is/application/restricted",
    >>>                         headers=nhsd_apim_auth_header
    >>>                         timeout=3)
    >>>     assert resp.status_code == 200
    """
    marker = request.node.get_closest_marker("nhsd_apim_authorization")
    if marker is None:
        return None

    if marker.args:
        authorization = Authorization(nhsd_apim_authorization=marker.args[0])
    else:
        authorization = Authorization(nhsd_apim_authorization=marker.kwargs)
    return authorization.dict()["nhsd_apim_authorization"]
