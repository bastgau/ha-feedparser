"""Bundled feedparser wrapper.

Self-contained: it knows nothing about Home Assistant. It turns the untyped objects of feedparser into typed ones.
"""

from __future__ import annotations

from .client import FeedClient, ParsedFeed
from .entry import IMAGE_REGEX, FeedEntry, find_image_url, find_link

__all__ = [
    "IMAGE_REGEX",
    "FeedClient",
    "FeedEntry",
    "ParsedFeed",
    "find_image_url",
    "find_link",
]
