"""Tests for the feed client."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from custom_components.feedparser.feedparser_wrapper import FeedClient
import pytest
import requests

if TYPE_CHECKING:
    from pathlib import Path

FEED = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test feed</title>
    <link>https://example.com</link>
    <description>Test feed</description>
    {items}
  </channel>
</rss>
"""
ITEM = "<item><title>{title}</title><link>https://example.com/{title}</link></item>"


def write_feed(path: Path, titles: list[str]) -> str:
    """Write a feed with the given item titles in a folder and return its file URL."""
    feed_path = path / "feed.xml"
    feed_path.write_text(FEED.format(items="".join(ITEM.format(title=title) for title in titles)), encoding="utf-8")
    return feed_path.as_uri()


def test_fetch_reads_a_local_feed(tmp_path: Path) -> None:
    """Test that a feed is read from a file URL and its entries are returned in order."""
    parsed_feed = FeedClient(user_agent="test").fetch(write_feed(tmp_path, ["first", "second"]))

    assert [entry["title"] for entry in parsed_feed.entries] == ["first", "second"]
    assert parsed_feed.entries[0]["link"] == "https://example.com/first"


def test_fetch_returns_no_entries_for_an_empty_feed(tmp_path: Path) -> None:
    """Test that a feed without items gives an empty list of entries."""
    assert not FeedClient(user_agent="test").fetch(write_feed(tmp_path, [])).entries


def test_fetch_sends_the_user_agent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that the configured User-Agent is the one sent with the request."""
    sent: list[str | bytes | None] = []
    original_get = requests.Session.get

    def spy_get(self: requests.Session, url: str, *args: Any, **kwargs: Any) -> requests.Response:
        response = original_get(self, url, *args, **kwargs)
        sent.append(response.request.headers.get("User-Agent"))
        return response

    monkeypatch.setattr(requests.Session, "get", spy_get)

    FeedClient(user_agent="Custom/1.0").fetch(write_feed(tmp_path, ["first"]))

    assert sent == ["Custom/1.0"]


def test_fetch_raises_on_an_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that an HTTP error status raises instead of being parsed as a feed."""

    def failing_get(_self: requests.Session, url: str, *_args: Any, **_kwargs: Any) -> requests.Response:
        response = requests.Response()
        response.status_code = 500
        response.url = url
        return response

    monkeypatch.setattr(requests.Session, "get", failing_get)

    with pytest.raises(requests.HTTPError):
        FeedClient(user_agent="test").fetch("https://example.com/feed.xml")
