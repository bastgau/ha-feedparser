"""Tests for the helpers reading the entries of a parsed feed."""

from __future__ import annotations

from custom_components.rss_feedparser.feedparser_wrapper import FeedEntry, find_image_url, find_link
import pytest


@pytest.mark.parametrize(
    ("entry", "expected"),
    [
        pytest.param(
            {"enclosures": [{"type": "image/png", "href": "https://example.com/a.png"}]},
            "https://example.com/a.png",
            id="image-enclosure",
        ),
        pytest.param(
            {
                "enclosures": [
                    {"type": "audio/mpeg", "href": "https://example.com/a.mp3"},
                    {"type": "image/jpeg", "href": "https://example.com/b.jpg"},
                ],
            },
            "https://example.com/b.jpg",
            id="first-image-enclosure-wins",
        ),
        pytest.param(
            {"enclosures": [{"href": "https://example.com/untyped"}]},
            None,
            id="enclosure-without-type",
        ),
        pytest.param(
            {"media_content": [{"url": "https://example.com/a.png", "type": "image/png"}]},
            "https://example.com/a.png",
            id="image-media-content",
        ),
        pytest.param(
            {
                "media_content": [
                    {"url": "https://example.com/a.mp4", "type": "video/mp4"},
                    {"url": "https://example.com/b.jpg", "type": "image/jpeg"},
                ],
            },
            "https://example.com/b.jpg",
            id="non-image-media-content-is-skipped",
        ),
        pytest.param(
            {"media_content": [{"url": "https://example.com/c"}]},
            None,
            id="media-content-without-type",
        ),
        pytest.param(
            {"summary": '<p>Text</p><img class="x" src="https://example.com/s.png" alt="y">'},
            "https://example.com/s.png",
            id="image-in-summary",
        ),
        pytest.param(
            {
                "enclosures": [{"type": "image/png", "href": "https://example.com/enclosure.png"}],
                "media_content": [{"url": "https://example.com/media.png", "type": "image/png"}],
                "summary": '<img src="https://example.com/summary.png" alt="y">',
            },
            "https://example.com/enclosure.png",
            id="enclosure-before-media-content-before-summary",
        ),
        pytest.param(
            {"media_content": [{"url": "https://example.com/media.png", "type": "image/png"}], "summary": "<p>x</p>"},
            "https://example.com/media.png",
            id="media-content-before-summary",
        ),
        pytest.param({"summary": "<p>No image here</p>"}, None, id="summary-without-image"),
        pytest.param({}, None, id="empty-entry"),
    ],
)
def test_find_image_url(entry: FeedEntry, expected: str | None) -> None:
    """Test that the first image is picked from enclosures, media:content or the summary, in that order."""
    assert find_image_url(entry) == expected


def test_find_link_returns_the_first_link() -> None:
    """Test that the first link of the entry is returned."""
    entry: FeedEntry = {"links": [{"href": "https://example.com/1"}, {"href": "https://example.com/2"}]}
    assert find_link(entry) == "https://example.com/1"


def test_find_link_without_links() -> None:
    """Test that an entry without links gives an empty string."""
    assert not find_link({})
