"""Client that fetches a feed, over HTTP or from a file, and parses it with feedparser."""

# feedparser ships no type information, so everything it returns is Unknown to Pyright.
# This module is the only one that talks to it: the checks are relaxed here and nowhere
# else, and callers receive fully typed objects.
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

import feedparser
import requests
from requests_file import FileAdapter

if TYPE_CHECKING:
    from .entry import FeedEntry


@dataclass(frozen=True)
class ParsedFeed:
    """A parsed feed.

    Attributes:
        entries (list[FeedEntry]): Entries of the feed, in the order of the feed.

    """

    entries: list[FeedEntry]


class FeedClient:  # pylint: disable=too-few-public-methods
    """Fetch and parse feeds.

    Attributes:
        user_agent (str): Value of the User-Agent header sent with every request.

    """

    def __init__(self, user_agent: str) -> None:
        """Initialize the client.

        Args:
            user_agent (str): Value of the User-Agent header sent with every request.

        """
        self.user_agent = user_agent

    def fetch(self, url: str) -> ParsedFeed:
        """Fetch a feed and parse it.

        Args:
            url (str): http, https or file URL of the feed.

        Returns:
            ParsedFeed: The parsed feed, whose entries are the feedparser objects, so their key aliases keep working.

        """
        session = requests.Session()
        session.mount("file://", FileAdapter())
        session.headers.update({"User-Agent": self.user_agent})
        response = session.get(url)
        response.raise_for_status()
        parsed_feed = feedparser.parse(response.text)
        return ParsedFeed(entries=cast("list[FeedEntry]", parsed_feed.entries))
