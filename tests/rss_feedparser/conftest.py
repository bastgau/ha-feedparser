"""Pytest configuration."""

from collections.abc import Iterator
from pathlib import Path
import socket

from custom_components.rss_feedparser.sensor import FeedParserSensor
import pytest

from tests.rss_feedparser.constants import TEST_FEEDS
from tests.rss_feedparser.feedsource import FeedSource

# Captured at import time, before the Home Assistant test plugin replaces it for each test.
_REAL_GETADDRINFO = socket.getaddrinfo

TWO_ITEMS_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
  <title>Local feed</title><link>https://example.com</link><description>Local feed</description>
  <item><title>First</title><link>https://example.com/first</link></item>
  <item><title>Second</title><link>https://example.com/second</link></item>
</channel></rss>
"""


@pytest.fixture
def local_feed_url(tmp_path: Path) -> str:
    """Write a feed with two items in a temporary folder.

    Args:
        tmp_path (Path): Temporary folder of the test.

    Returns:
        str: file URL of the feed.

    """
    feed_path = tmp_path / "local_feed.xml"
    feed_path.write_text(TWO_ITEMS_FEED, encoding="utf-8")
    return feed_path.as_uri()


@pytest.fixture
def network_enabled(socket_enabled: None) -> Iterator[None]:  # pylint: disable=unused-argument
    """Allow a test to reach real remote servers.

    The Home Assistant test plugin blocks sockets, only lets connections to 127.0.0.1 through and replaces
    DNS resolution with a function that rejects every host name. `socket_enabled` only lifts the first
    restriction, so this fixture also allows connections to any address and restores the real resolver for
    the duration of the test. pytest-socket puts its own restrictions back when the test ends.

    pytest-socket is looked up here and not at the top of the file: this conftest is also loaded by the
    client tests, whose environment does not install it (nor does any client test use this fixture).

    Args:
        socket_enabled (None): Upstream fixture re-enabling sockets.

    Yields:
        None: Control to the test, with connections and the real DNS resolver allowed.

    """
    pytest_socket = pytest.importorskip("pytest_socket")
    pytest_socket.socket_allow_hosts(["0.0.0.0/0", "::/0"], allow_unix_socket=True)
    patched_getaddrinfo = socket.getaddrinfo
    socket.getaddrinfo = _REAL_GETADDRINFO
    yield
    socket.getaddrinfo = patched_getaddrinfo


def get_feeds() -> list[FeedSource]:
    """Return list of feeds represented by FeedSource objects.

    Returns:
        list[FeedSource]: One FeedSource per feed of TEST_FEEDS.

    """
    return [FeedSource(feed) for feed in TEST_FEEDS]


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    """Generate tests and fixtures.

    Args:
        metafunc (pytest.Metafunc): Pytest object describing the test function being collected.

    """
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
    """Return feed file source.

    Args:
        request (pytest.FixtureRequest): Request carrying the parametrized feed.

    Returns:
        FeedSource: The feed of the current parametrization.

    """
    return request.param


@pytest.fixture
def feed_sensor(feed: FeedSource) -> FeedParserSensor:  # pylint: disable=redefined-outer-name
    """Return feed sensor initialized with the local RSS feed.

    Args:
        feed (FeedSource): The feed of the current parametrization.

    Returns:
        FeedParserSensor: A sensor reading the local copy of the feed.

    """
    return FeedParserSensor(**feed.sensor_config_local_feed)


@pytest.fixture
def feed_with_image_in_summary(
    request: pytest.FixtureRequest,
) -> FeedSource:
    """Return feed sensor with images in summary of its entries.

    Args:
        request (pytest.FixtureRequest): Request carrying the parametrized feed.

    Returns:
        FeedSource: A feed whose entries have images in their summary.

    """
    return request.param
