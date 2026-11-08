"""Tests for the config flow, the options flow and the setup of a config entry."""

from __future__ import annotations

from datetime import timedelta
import json
from pathlib import Path
import re
from typing import TYPE_CHECKING, Any

from custom_components.rss_feedparser.config_flow import FeedparserConfigFlow
from custom_components.rss_feedparser.const import (
    CONF_DATE_FORMAT,
    CONF_EXCLUSIONS,
    CONF_FEED_URL,
    CONF_INCLUSIONS,
    CONF_LOCAL_TIME,
    CONF_REMOVE_SUMMARY_IMG,
    CONF_SHOW_TOPN,
    CONF_USER_AGENT,
    DOMAIN,
    USER_AGENT,
)
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.config_entries import SOURCE_USER, ConfigEntryState
from homeassistant.const import CONF_NAME, CONF_SCAN_INTERVAL
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_platform

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

COMPONENT_PATH = Path(__file__).parents[2] / "custom_components" / "rss_feedparser"
THIRTY_MINUTES = {"hours": 0, "minutes": 30, "seconds": 0}


def _user_input(feed_url: str, **overrides: Any) -> dict[str, Any]:
    """Build the data submitted by the setup form, with the given fields replacing the defaults."""
    return {
        CONF_NAME: "Test feed",
        CONF_FEED_URL: feed_url,
        CONF_DATE_FORMAT: "%Y-%m-%d",
        CONF_LOCAL_TIME: False,
        CONF_SCAN_INTERVAL: THIRTY_MINUTES,
        CONF_SHOW_TOPN: 1,
        CONF_REMOVE_SUMMARY_IMG: False,
        CONF_INCLUSIONS: ["title", "link"],
        CONF_EXCLUSIONS: [],
        CONF_USER_AGENT: "Custom/1.0",
    } | overrides


async def _start_flow(hass: HomeAssistant) -> str:
    """Open the setup form and return the id of the flow, which waits for the form data."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    return result["flow_id"]


async def _add_entry(hass: HomeAssistant, feed_url: str) -> MockConfigEntry:
    """Create and set up a config entry following a feed, and return it."""
    user_input = _user_input(feed_url)
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test feed",
        unique_id=feed_url,
        data={CONF_NAME: user_input[CONF_NAME], CONF_FEED_URL: feed_url},
        options={key: value for key, value in user_input.items() if key not in {CONF_NAME, CONF_FEED_URL}},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_user_flow_creates_an_entry(hass: HomeAssistant, local_feed_url: str) -> None:
    """Test that the setup form creates an entry and the sensor of the feed."""
    flow_id = await _start_flow(hass)

    result = await hass.config_entries.flow.async_configure(flow_id, _user_input(local_feed_url))
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Test feed"
    assert result["data"] == {CONF_NAME: "Test feed", CONF_FEED_URL: local_feed_url}
    assert result["options"][CONF_SCAN_INTERVAL] == THIRTY_MINUTES
    assert result["options"][CONF_SHOW_TOPN] == 1
    assert result["options"][CONF_USER_AGENT] == "Custom/1.0"
    state = hass.states.get("sensor.test_feed")
    assert state is not None
    assert state.state == "1"
    assert [entry["title"] for entry in state.attributes["entries"]] == ["First"]


async def test_user_flow_form_defaults(hass: HomeAssistant, local_feed_url: str) -> None:
    """Test that the optional fields can be left out and that the default User-Agent is used."""
    flow_id = await _start_flow(hass)
    user_input = _user_input(local_feed_url)
    for field in (CONF_INCLUSIONS, CONF_EXCLUSIONS, CONF_USER_AGENT):
        del user_input[field]

    result = await hass.config_entries.flow.async_configure(flow_id, user_input)

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["options"][CONF_INCLUSIONS] == []
    assert result["options"][CONF_EXCLUSIONS] == []
    assert result["options"][CONF_USER_AGENT] == USER_AGENT


@pytest.mark.parametrize("bad_url", ["not a url", "ftp://example.com/feed.xml", "example.com/feed.xml"])
async def test_user_flow_rejects_an_invalid_url(hass: HomeAssistant, bad_url: str) -> None:
    """Test that an address without a supported scheme is refused."""
    flow_id = await _start_flow(hass)

    result = await hass.config_entries.flow.async_configure(flow_id, _user_input(bad_url))

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_FEED_URL: "invalid_url"}


async def test_user_flow_reports_an_unreachable_feed(hass: HomeAssistant, tmp_path: Path) -> None:
    """Test that a feed which cannot be fetched is refused."""
    flow_id = await _start_flow(hass)
    missing_feed = (tmp_path / "missing.xml").as_uri()

    result = await hass.config_entries.flow.async_configure(flow_id, _user_input(missing_feed))

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_user_flow_rejects_a_too_short_interval(hass: HomeAssistant, local_feed_url: str) -> None:
    """Test that a refresh interval under one minute is refused."""
    flow_id = await _start_flow(hass)

    result = await hass.config_entries.flow.async_configure(
        flow_id, _user_input(local_feed_url, **{CONF_SCAN_INTERVAL: {"hours": 0, "minutes": 0, "seconds": 30}})
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_SCAN_INTERVAL: "scan_interval_too_short"}


async def test_user_flow_aborts_when_the_feed_is_already_configured(hass: HomeAssistant, local_feed_url: str) -> None:
    """Test that a feed can only be followed by one config entry."""
    MockConfigEntry(domain=DOMAIN, unique_id=local_feed_url).add_to_hass(hass)
    flow_id = await _start_flow(hass)

    result = await hass.config_entries.flow.async_configure(flow_id, _user_input(local_feed_url))

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_entry_sets_the_polling_interval_of_its_platform(hass: HomeAssistant, local_feed_url: str) -> None:
    """Test that the refresh interval of the entry becomes the polling interval of its sensor."""
    entry = await _add_entry(hass, local_feed_url)

    platforms = [
        platform
        for platform in entity_platform.async_get_platforms(hass, DOMAIN)
        if platform.config_entry is not None and platform.config_entry.entry_id == entry.entry_id
    ]

    assert [platform.scan_interval for platform in platforms] == [timedelta(minutes=30)]


async def test_entry_can_be_unloaded(hass: HomeAssistant, local_feed_url: str) -> None:
    """Test that unloading the entry removes its sensor."""
    entry = await _add_entry(hass, local_feed_url)
    assert entry.state is ConfigEntryState.LOADED

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.NOT_LOADED
    state = hass.states.get("sensor.test_feed")
    assert state is not None
    assert state.state == "unavailable"


async def test_entries_attribute_is_kept_out_of_the_recorder(hass: HomeAssistant, local_feed_url: str) -> None:
    """Test that the entries stay available live but are excluded from the recorder, which drops large attributes."""
    await _add_entry(hass, local_feed_url)

    state = hass.states.get("sensor.test_feed")

    assert state is not None
    assert [entry["title"] for entry in state.attributes["entries"]] == ["First"]
    assert state.state_info is not None
    assert "entries" in state.state_info["unrecorded_attributes"]


async def test_options_flow_updates_the_entry_and_reloads_it(hass: HomeAssistant, local_feed_url: str) -> None:
    """Test that saved options are stored and applied by reloading the entry."""
    entry = await _add_entry(hass, local_feed_url)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    new_options = _user_input(local_feed_url, **{CONF_SHOW_TOPN: 2, CONF_INCLUSIONS: ["title"]})
    del new_options[CONF_NAME]
    del new_options[CONF_FEED_URL]
    result = await hass.config_entries.options.async_configure(result["flow_id"], new_options)
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_SHOW_TOPN] == 2
    assert entry.options[CONF_INCLUSIONS] == ["title"]
    state = hass.states.get("sensor.test_feed")
    assert state is not None
    assert state.state == "2"
    assert [item["title"] for item in state.attributes["entries"]] == ["First", "Second"]


async def test_options_flow_rejects_a_too_short_interval(hass: HomeAssistant, local_feed_url: str) -> None:
    """Test that the options form refuses a refresh interval under one minute."""
    entry = await _add_entry(hass, local_feed_url)
    result = await hass.config_entries.options.async_init(entry.entry_id)

    new_options = _user_input(local_feed_url, **{CONF_SCAN_INTERVAL: {"hours": 0, "minutes": 0, "seconds": 10}})
    del new_options[CONF_NAME]
    del new_options[CONF_FEED_URL]
    result = await hass.config_entries.options.async_configure(result["flow_id"], new_options)

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_SCAN_INTERVAL: "scan_interval_too_short"}


def test_translations_match_strings() -> None:
    """Test that the English translation is the same file as the source strings."""
    strings = json.loads((COMPONENT_PATH / "strings.json").read_text(encoding="utf-8"))
    english = json.loads((COMPONENT_PATH / "translations" / "en.json").read_text(encoding="utf-8"))
    assert strings == english


def _strings_of(value: object) -> list[str]:
    """Collect every string found in a loaded JSON document."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [text for item in value.values() for text in _strings_of(item)]
    return []


def test_translations_contain_no_html() -> None:
    """Test that no translated text contains a tag, which hassfest refuses."""
    for name in ("strings.json", "translations/en.json"):
        document = json.loads((COMPONENT_PATH / name).read_text(encoding="utf-8"))
        assert [text for text in _strings_of(document) if re.search(r"<[^>]*>", text)] == [], name


@pytest.mark.parametrize(
    ("section", "step"),
    [("config", "user"), ("options", "init")],
)
def test_every_form_field_has_a_label_and_a_description(section: str, step: str) -> None:
    """Test that each field of the forms is translated and described."""
    strings = json.loads((COMPONENT_PATH / "strings.json").read_text(encoding="utf-8"))
    form = strings[section]["step"][step]
    assert set(form["data"]) >= set(form["data_description"])
    expected_fields = {
        CONF_DATE_FORMAT,
        CONF_LOCAL_TIME,
        CONF_SCAN_INTERVAL,
        CONF_SHOW_TOPN,
        CONF_REMOVE_SUMMARY_IMG,
        CONF_INCLUSIONS,
        CONF_EXCLUSIONS,
        CONF_USER_AGENT,
    }
    if step == "user":
        expected_fields |= {CONF_NAME, CONF_FEED_URL}
    assert set(form["data"]) == expected_fields


def test_config_flow_has_a_version() -> None:
    """Test that the config flow declares the version of the entries it creates."""
    assert FeedparserConfigFlow.VERSION == 1
