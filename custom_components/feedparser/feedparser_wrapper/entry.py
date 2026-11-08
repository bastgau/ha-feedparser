"""Helpers to read the entries of a parsed feed."""

from __future__ import annotations

import re
from typing import Any

IMAGE_REGEX = r"<img.+?src=\"(.+?)\".+?>"

# An entry is a mapping whose keys depend on the feed: feedparser returns whatever the feed contains.
type FeedEntry = dict[str, Any]


def find_image_url(entry: FeedEntry) -> str | None:
    """Return the URL of the first image of an entry.

    The image enclosures are looked at first, then the image media:content elements, then the <img> tags of the summary.

    Args:
        entry (FeedEntry): Entry of a parsed feed.

    Returns:
        str | None: URL of the first image found, or None when the entry has no image.

    """
    if entry.get("enclosures"):
        images = [enc for enc in entry["enclosures"] if enc.get("type", "").startswith("image/")]
        if images:
            return images[0]["href"]
    if entry.get("media_content"):
        # "type" is optional in media:content, so don't assume it is present
        images = [
            media for media in entry["media_content"] if media.get("type", "").startswith("image/") and media.get("url")
        ]
        if images:
            return images[0]["url"]
    if "summary" in entry:
        summary_images: list[str] = re.findall(IMAGE_REGEX, entry["summary"])
        if summary_images:
            return summary_images[0]
    return None


def find_link(entry: FeedEntry) -> str:
    """Return the link of an entry.

    Args:
        entry (FeedEntry): Entry of a parsed feed.

    Returns:
        str: URL of the first link of the entry, or an empty string when the entry has none.

    """
    if "links" in entry:
        return entry["links"][0]["href"]
    return ""
