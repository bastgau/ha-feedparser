"""Pytest configuration."""

from collections.abc import Iterator
import socket

from custom_components.feedparser.sensor import FeedParserSensor
import pytest

from tests.feedparser.constants import TEST_FEEDS
from tests.feedparser.feedsource import FeedSource

# Captured at import time, before the Home Assistant test plugin replaces it for each test.
_REAL_GETADDRINFO = socket.getaddrinfo


@pytest.fixture
def network_enabled(socket_enabled: None) -> Iterator[None]:  # pylint: disable=unused-argument
    """Allow a test to reach real remote servers.

    The Home Assistant test plugin blocks sockets and replaces DNS resolution with a
    function that rejects every host name. `socket_enabled` lifts the first restriction,
    this fixture restores the real resolver for the duration of the test.
    """
    patched_getaddrinfo = socket.getaddrinfo
    socket.getaddrinfo = _REAL_GETADDRINFO
    yield
    socket.getaddrinfo = patched_getaddrinfo


def get_feeds() -> list[FeedSource]:
    """Return list of feeds represented by FeedSource objects."""
    return [FeedSource(feed) for feed in TEST_FEEDS]


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    """Generate tests and fixtures."""
    feeds = get_feeds()
    if "feed" in metafunc.fixturenames:
        metafunc.parametrize("feed", feeds, ids=[f.name for f in feeds], indirect=True)
    if "feed_with_image_in_summary" in metafunc.fixturenames:
        feeds_with_image_in_summary = [
            pytest.param(
                feed,
                id=feed.name,
            )
            for feed in feeds
            if feed.has_images_in_summary
        ]
        metafunc.parametrize(
            "feed_with_image_in_summary",
            feeds_with_image_in_summary,
            indirect=True,
        )


@pytest.fixture
def feed(request: pytest.FixtureRequest) -> FeedSource:
    """Return feed file source."""
    return request.param


@pytest.fixture
def feed_sensor(feed: FeedSource) -> FeedParserSensor:
    """Return feed sensor initialized with the local RSS feed."""
    return FeedParserSensor(**feed.sensor_config_local_feed)


@pytest.fixture
def feed_with_image_in_summary(
    request: pytest.FixtureRequest,
) -> FeedSource:
    """Return feed sensor with images in summary of its entries."""
    return request.param
