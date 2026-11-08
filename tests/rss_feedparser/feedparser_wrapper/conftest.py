"""Fixtures for the bundled client's own tests.

These tests cover `custom_components/rss_feedparser/feedparser_wrapper/`, which knows nothing about Home Assistant. This
file keeps that true at the test level too, so the suite can run in an environment where Home Assistant is not
installed at all.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations() -> None:
    """Neutralize the root conftest's Home Assistant fixture for this package.

    `tests/conftest.py` declares an autouse fixture that pulls in `enable_custom_integrations`, which only exists
    once pytest-homeassistant-custom-component is installed. Overriding it here (a fixture defined in a nested
    conftest shadows its parent's) drops that dependency for the client tests.

    """
