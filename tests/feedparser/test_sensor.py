"""Tests the feedparser sensor."""

from contextlib import nullcontext, suppress
from datetime import UTC, datetime
import re
from typing import TYPE_CHECKING, Any

from custom_components.feedparser.sensor import (
    CONF_USER_AGENT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_THUMBNAIL,
    IMAGE_REGEX,
    PLATFORM_SCHEMA,
    USER_AGENT,
    FeedParserSensor,
)
import feedparser
import pytest
import requests

from homeassistant.util import dt as dt_util
from tests.feedparser.constants import DATE_FORMAT, URLS_HEADERS_REQUIRED
from tests.feedparser.feedsource import FeedSource

if TYPE_CHECKING:
    from collections.abc import Callable
    import time


def test_simple(feed_sensor: FeedParserSensor) -> None:
    """Test simple."""
    feed_sensor.update()
    assert feed_sensor.feed_entries


def test_update_sensor(feed: FeedSource) -> None:
    """Test instantiate sensor."""
    feed_sensor = FeedParserSensor(
        feed=feed.path.absolute().as_uri(),
        name=feed.name,
        date_format=feed.sensor_config.date_format,
        local_time=feed.sensor_config.local_time,
        show_topn=feed.sensor_config.show_topn,
        remove_summary_image=feed.sensor_config.remove_summary_image,
        inclusions=feed.sensor_config.inclusions,
        exclusions=feed.sensor_config.exclusions,
        scan_interval=feed.sensor_config.scan_interval,
    )
    feed_sensor.update()
    assert feed_sensor.feed_entries

    # assert that the sensor value is equal to the number of entries
    assert feed_sensor.native_value == len(feed_sensor.feed_entries)

    # assert that all entries have a title
    assert all(e["title"] for e in feed_sensor.feed_entries)

    # assert that all entries have a link
    assert all(e["link"] for e in feed_sensor.feed_entries)

    # assert that all entries have a published date
    assert all(e["published"] for e in feed_sensor.feed_entries)

    # assert that all entries have non-default image
    if feed.all_entries_have_images and "image" in feed.sensor_config.inclusions:
        if feed.has_images:
            assert all(e["image"] != DEFAULT_THUMBNAIL for e in feed_sensor.feed_entries), (
                "Default image found for entry that should have an image"
            )
        else:
            assert all(e["image"] == DEFAULT_THUMBNAIL for e in feed_sensor.feed_entries), (
                "Non-default image found for entry that should not have an image"
            )

    # assert that all entries have a unique link
    if feed.has_unique_links:
        assert len({e["link"] for e in feed_sensor.feed_entries}) == len(
            feed_sensor.feed_entries,
        ), "Duplicate links found"

    # assert that all entries have a unique title
    if feed.has_unique_titles:
        assert len({e["title"] for e in feed_sensor.feed_entries}) == len(
            feed_sensor.feed_entries,
        ), "Duplicate titles found"

    # assert that all entries have a unique published date
    if feed.has_unique_dates:
        assert len({e["published"] for e in feed_sensor.feed_entries}) == len(
            feed_sensor.feed_entries,
        ), "Duplicate published dates found"

    # assert that all entries have a unique image
    if feed.has_images and feed.has_unique_images:
        assert len({e["image"] for e in feed_sensor.feed_entries}) == len(
            feed_sensor.feed_entries,
        ), "Duplicate images found"


def test_update_sensor_with_topn(feed: FeedSource) -> None:
    """Test that the sensor stores only the topn entries."""
    show_topn = 1
    feed_sensor = FeedParserSensor(
        feed=feed.path.absolute().as_uri(),
        name=feed.name,
        date_format=DATE_FORMAT,
        local_time=False,
        show_topn=show_topn,
        remove_summary_image=False,
        inclusions=["image", "title", "link", "published"],
        exclusions=[],
        scan_interval=DEFAULT_SCAN_INTERVAL,
    )
    feed_sensor.update()
    assert feed_sensor.feed_entries

    # assert that the sensor value is equal to the number of
    # entries and that only top N entries are stored
    assert feed_sensor.native_value == show_topn == len(feed_sensor.feed_entries)


@pytest.mark.parametrize(
    "local_time",
    [True, False],
    ids=["local_time", "default_time"],
)
def test_update_sensor_entries_time(
    feed: FeedSource,
    feed_sensor: FeedParserSensor,
    local_time: bool,
) -> None:
    """Test that the sensor converts the published date to local time."""
    # The Home Assistant test fixtures default the local time zone to US/Pacific;
    # this test compares the sensor dates with UTC dates from the feed.
    dt_util.set_default_time_zone(UTC)
    feed_sensor.local_time = local_time
    feed_sensor.update()
    assert feed_sensor.feed_entries

    # load the feed with feedparser
    parsed_feed: feedparser.FeedParserDict = feedparser.parse(
        feed.path.absolute().as_uri(),
    )

    # get the first entry
    entry = parsed_feed.entries[0]

    # get the time of the first entry
    first_entry_struct_time: time.struct_time = entry.published_parsed
    first_entry_time: datetime = datetime(*first_entry_struct_time[:6], tzinfo=UTC)

    # get the time of the first entry in the sensor
    first_sensor_entry_time: datetime = datetime.strptime(  # noqa: DTZ007
        feed_sensor.feed_entries[0]["published"],
        feed.sensor_config.date_format,
    )

    if not first_sensor_entry_time.tzinfo:
        first_sensor_entry_time = first_sensor_entry_time.replace(tzinfo=UTC)

    # assert that the time of the first entry in the sensor is equal to
    # the time of the first entry in the feed
    assert first_entry_time == first_sensor_entry_time


def test_check_duplicates(feed_sensor: FeedParserSensor) -> None:
    """Test that the sensor stores only unique entries."""
    feed_sensor.update()
    assert feed_sensor.extra_state_attributes["entries"]
    after_first_update = len(feed_sensor.feed_entries)
    feed_sensor.update()
    after_second_update = len(feed_sensor.feed_entries)
    assert after_first_update == after_second_update


@pytest.mark.parametrize(
    "online_feed",
    URLS_HEADERS_REQUIRED,
    ids=lambda feed_url: feed_url["name"],
)
def test_fetch_data_headers_required(
    online_feed: dict,
    network_enabled: None,  # pylint: disable=unused-argument
) -> None:
    """Test fetching feed from remote server that requires request with headers."""
    feed_sensor = FeedParserSensor(
        feed=online_feed["url"],
        name=online_feed["name"],
        date_format=DATE_FORMAT,
        local_time=False,
        show_topn=9999,
        remove_summary_image=False,
        inclusions=["image", "title", "link", "published"],
        exclusions=[],
        scan_interval=DEFAULT_SCAN_INTERVAL,
    )
    feed_sensor.update()
    assert feed_sensor.feed_entries


def test_remove_summary_image(
    feed_with_image_in_summary: FeedSource,
) -> None:
    """Test that the sensor removes the image from the summary."""
    feed = feed_with_image_in_summary
    feed_sensor = FeedParserSensor(
        **feed.sensor_config_local_feed | {"remove_summary_image": False},
    )
    feed_sensor.update()
    assert feed_sensor.feed_entries

    # assert that the sensor does not remove the image from the summary
    assert any(re.search(IMAGE_REGEX, e["summary"]) is not None for e in feed_sensor.feed_entries)

    feed_sensor = FeedParserSensor(
        **feed.sensor_config_local_feed | {"remove_summary_image": True},
    )
    feed_sensor.update()
    assert feed_sensor.feed_entries

    with nullcontext() if feed.all_entries_have_summary else suppress(KeyError):
        assert all("img" not in e["summary"] for e in feed_sensor.feed_entries)


def test_image_not_in_entries(feed: FeedSource) -> None:
    """Test that the sensor does not include the image in any feed entry."""
    # keep only the title in the inclusions
    feed_sensor = FeedParserSensor(
        **feed.sensor_config_local_feed | {"inclusions": ["title"]},
    )
    feed_sensor.update()
    assert feed_sensor.feed_entries
    # assert that the sensor does not include the image in its feed entries
    assert all("image" not in e for e in feed_sensor.feed_entries)


@pytest.fixture
def sent_user_agents(monkeypatch: pytest.MonkeyPatch) -> list[str | bytes | None]:
    """Record the User-Agent header of every request the sensor sends."""
    sent: list[str | bytes | None] = []
    original_get: Callable[..., requests.Response] = requests.Session.get

    def spy_get(
        self: requests.Session,
        url: str,
        *args: Any,
        **kwargs: Any,
    ) -> requests.Response:
        response = original_get(self, url, *args, **kwargs)
        sent.append(response.request.headers.get("User-Agent"))
        return response

    monkeypatch.setattr(requests.Session, "get", spy_get)
    return sent


def test_default_user_agent(
    feed: FeedSource,
    sent_user_agents: list[str | bytes | None],  # pylint: disable=redefined-outer-name
) -> None:
    """Test that the integration's User-Agent is sent when none is configured."""
    feed_sensor = FeedParserSensor(**feed.sensor_config_local_feed)
    feed_sensor.update()
    assert sent_user_agents == [USER_AGENT]


def test_custom_user_agent(
    feed: FeedSource,
    sent_user_agents: list[str | bytes | None],  # pylint: disable=redefined-outer-name
) -> None:
    """Test that a configured User-Agent replaces the default one."""
    custom_user_agent = "Mozilla/5.0 (compatible; FeedTest/1.0)"
    feed_sensor = FeedParserSensor(
        **feed.sensor_config_local_feed | {"user_agent": custom_user_agent},
    )
    feed_sensor.update()
    assert sent_user_agents == [custom_user_agent]


def test_user_agent_config_schema() -> None:
    """Test that user_agent is optional and defaults to the integration's agent."""
    base_config = {
        "platform": "feedparser",
        "name": "Test Feed",
        "feed_url": "https://example.com/feed.xml",
    }
    assert PLATFORM_SCHEMA(base_config)[CONF_USER_AGENT] == USER_AGENT

    custom_config = base_config | {CONF_USER_AGENT: "Custom/1.0"}
    assert PLATFORM_SCHEMA(custom_config)[CONF_USER_AGENT] == "Custom/1.0"


@pytest.mark.parametrize(
    ("media_content", "expected"),
    [
        # image with an explicit type
        (
            [{"url": "https://example.com/a.png", "type": "image/png"}],
            "https://example.com/a.png",
        ),
        # non-image media is skipped, the first image wins
        (
            [
                {"url": "https://example.com/a.mp4", "type": "video/mp4"},
                {"url": "https://example.com/b.jpg", "type": "image/jpeg"},
            ],
            "https://example.com/b.jpg",
        ),
        # media:content without a "type" attribute must not raise a KeyError
        ([{"url": "https://example.com/c"}], DEFAULT_THUMBNAIL),
    ],
)
def test_process_image_media_content(
    feed: FeedSource,
    media_content: list[dict[str, str]],
    expected: str,
) -> None:
    """Test that images are picked from media:content, with or without a type."""
    feed_sensor = FeedParserSensor(**feed.sensor_config_local_feed)
    entry = feedparser.FeedParserDict({"media_content": media_content})
    assert feed_sensor._process_image(entry) == expected  # pylint: disable=protected-access
