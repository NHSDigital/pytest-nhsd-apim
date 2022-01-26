"""
This module defined all the pytest config.

- command line flags
- ini options
- custom markers

And a few fixtures to pull that config in.
"""
import os

import pytest


_PYTEST_CONFIG = {
    "--apigee-proxy-name": {
        "help": "Proxy under test, should exactly match the name on Apigee."
    },
    "--apigee-access-token": {
        "help": "Access token to log into apigee edge API, output of get_token"
    },
    "--apigee-organization": {
        "help": "nhsd-nonprod/nhsd-prod.",
        "default": "nhsd-nonprod",
    },
    "--apigee-developer": {
        "help": "Developer that will own the test app.",
        "default": "apm-testing-internal-dev@nhs.net",
    },
}


def _flag_to_dest(flag):
    # e.g. --apigee-access-token is stored as APIGEE_ACCESS_TOKEN
    return flag[2:].replace("-", "_").upper()


def pytest_addoption(parser):
    """
    Hook for cli options.

    Pytest calls this at some point to get command line flags into the
    request.config object.

    I also want to be able to define sensitive config, e.g.
    apigee_access_token via environment variables.
    """

    group = parser.getgroup("nhsd-apim")
    for flag, attrs in _PYTEST_CONFIG.items():
        group.addoption(
            flag,
            action="store",
            dest=_flag_to_dest(flag),
            help=attrs.get("help"),
            default=attrs.get("default"),
        )


def pytest_configure(config):
    """
    Hook for defining markers.
    """
    config.addinivalue_line(
        "markers",
        "product_scope(scope): Marker to indicate a required scope when selecting a product to register our test application to",
    )


@pytest.fixture(scope="session")
def nhsd_apim_config(request):
    """
    Use this fixture to access the config.
    It check environment variables as well as the CLI.
    """
    def _get_config(flag):
        name = _flag_to_dest(flag)

        cmd_line_value = getattr(request.config.option, name)
        if cmd_line_value is not None:
            return cmd_line_value

        env_var_value = os.environ.get(name)
        if env_var_value is not None:
            return env_var_value

        raise ValueError(
            f"Missing required config. You must pass cli option {flag} or environment variable {name}."
        )
    
    return {_flag_to_dest(flag): _get_config(flag) for flag in _PYTEST_CONFIG}
