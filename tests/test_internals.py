"""
These tests are for the internal fixtures.

These could be refactored at any time, do not depend on them!
"""

import pytest


def test_blank_app(_test_app):
    for credentials in _test_app["credentials"]:
        assert credentials["apiProducts"] == []
