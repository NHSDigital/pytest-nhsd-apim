"""
This module defines all the pytest config.

- command line flags
- ini options
- custom markers

And a few fixtures to pull that config in.
"""
import os
from datetime import datetime

import pytest
import logging

LOG = logging.getLogger(__name__)

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
    "--jwt-public-key-id": {
        "help": "Key ID ('kid') to select particular key.",
        "default": "test-1",
    },
    # TODO: Add these if the user wishes...
    # "--jwt-public-key-url": {
    #     "help": "URL of JWT public key. Must be used with --jwt-private-key-file.",
    #     "default": None
    # },
    # "--jwt-private-key-file": {
    #     "help": "Path to private key of JWT. Must be used with --jwt-public-key-url.",
    #     "default": None,
    # }
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
    marker_descr = "Marker to indicate a required scope when selecting a product to register our test application to."
    config.addinivalue_line(
        "markers",
        f"product_scope(scope): {marker_descr}")

    if not config.option.log_file:
        timestamp = datetime.strftime(datetime.now(), '%Y%m%d_%H%M%S')
        config.option.log_file = f'../logs/pytest_nhsd_apim_{timestamp}.log'


@pytest.fixture(scope="session")
def nhsd_apim_config(request):
    """
    Use this fixture to access this pytest extension's config.
    It checks environment variables as well as the CLI.
    """
    def _get_config(flag):
        name = _flag_to_dest(flag)

        cmd_line_value = getattr(request.config.option, name)
        if cmd_line_value is not None:
            return cmd_line_value

        env_var_value = os.environ.get(name)
        if env_var_value is not None:
            return env_var_value
        ve_msg = f"Missing required config. You must pass cli option {flag} or environment variable {name}."
        raise ValueError(ve_msg)
    
    return {_flag_to_dest(flag): _get_config(flag) for flag in _PYTEST_CONFIG}
