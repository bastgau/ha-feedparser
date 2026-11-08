"""Feedparser sensor."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import email.utils
import logging
import re
from typing import TYPE_CHECKING, Any

from dateutil import parser
import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorEntity
from homeassistant.const import CONF_NAME, CONF_SCAN_INTERVAL
import homeassistant.helpers.config_validation as cv
from homeassistant.util import dt

from .feedparser_wrapper import IMAGE_REGEX, FeedClient, find_image_url, find_link

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback
    from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

    from .feedparser_wrapper import FeedEntry, ParsedFeed

__version__ = "0.1.11"

COMPONENT_REPO = "https://github.com/custom-components/feedparser/"

REQUIREMENTS = ["feedparser"]

CONF_FEED_URL = "feed_url"
CONF_DATE_FORMAT = "date_format"
CONF_LOCAL_TIME = "local_time"
CONF_INCLUSIONS = "inclusions"
CONF_EXCLUSIONS = "exclusions"
CONF_SHOW_TOPN = "show_topn"
CONF_REMOVE_SUMMARY_IMG = "remove_summary_image"
CONF_USER_AGENT = "user_agent"

DEFAULT_DATE_FORMAT = "%a, %b %d %I:%M %p"
DEFAULT_SCAN_INTERVAL = timedelta(hours=1)
DEFAULT_THUMBNAIL = "https://www.home-assistant.io/images/favicon-192x192-full.png"
DEFAULT_TOPN = 9999
USER_AGENT = f"Home Assistant Feed-parser Integration {__version__}"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(  # pyright: ignore[reportConstantRedefinition]
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_FEED_URL): cv.string,
        vol.Required(CONF_DATE_FORMAT, default=DEFAULT_DATE_FORMAT): cv.string,
        vol.Optional(CONF_LOCAL_TIME, default=False): cv.boolean,
        vol.Optional(CONF_SHOW_TOPN, default=DEFAULT_TOPN): cv.positive_int,
        vol.Optional(CONF_REMOVE_SUMMARY_IMG, default=False): cv.boolean,
        vol.Optional(CONF_INCLUSIONS, default=[]): vol.All(cv.ensure_list, [cv.string]),
        vol.Optional(CONF_EXCLUSIONS, default=[]): vol.All(cv.ensure_list, [cv.string]),
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): cv.time_period,
        vol.Optional(CONF_USER_AGENT, default=USER_AGENT): cv.string,
    },
)

_LOGGER: logging.Logger = logging.getLogger(__name__)


async def async_setup_platform(
    hass: HomeAssistant,  # noqa: ARG001
    config: ConfigType,
    async_add_devices: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,  # noqa: ARG001
) -> None:
    """Set up the Feedparser sensor.

    Args:
        hass (HomeAssistant): Home Assistant instance, unused.
        config (ConfigType): Validated platform configuration of the sensor.
        async_add_devices (AddEntitiesCallback): Callback registering the entities of the platform.
        discovery_info (DiscoveryInfoType | None): Discovery data, unused.

    """
    async_add_devices(
        [
            FeedParserSensor(
                feed=config[CONF_FEED_URL],
                name=config[CONF_NAME],
                date_format=config[CONF_DATE_FORMAT],
                show_topn=config[CONF_SHOW_TOPN],
                remove_summary_image=config[CONF_REMOVE_SUMMARY_IMG],
                inclusions=config[CONF_INCLUSIONS],
                exclusions=config[CONF_EXCLUSIONS],
                scan_interval=config[CONF_SCAN_INTERVAL],
                local_time=config[CONF_LOCAL_TIME],
                user_agent=config[CONF_USER_AGENT],
            ),
        ],
        update_before_add=True,
    )


class FeedParserSensor(SensorEntity):  # pylint: disable=too-many-instance-attributes
    """Representation of a Feedparser sensor.

    Attributes:
        _attr_force_update (bool): Update the entity even when the number of entries did not change.
        _feed (str): URL of the feed.
        _attr_name (str): Name of the sensor.
        _attr_icon (str): Icon of the sensor.
        _date_format (str): strftime format of the dates of the entries.
        _show_topn (int): Maximum number of entries kept.
        _remove_summary_image (bool): Whether to strip the <img> tags from the summary of the entries.
        _inclusions (list[str | None]): Fields kept in the entries, all of them when empty.
        _exclusions (list[str | None]): Fields removed from the entries.
        _scan_interval (timedelta): Time between two updates of the feed.
        _local_time (bool): Whether the dates of the entries are converted to the local time zone.
        _user_agent (str): Value of the User-Agent header sent when fetching the feed.
        _entries (list[dict[str, Any]]): Entries of the feed, as exposed by the sensor.
        _attr_extra_state_attributes (dict[str, list[dict[str, Any]]]): State attributes of the sensor.
        _attr_attribution (str): Attribution shown for the data of the sensor.

    """

    # force update the entity since the number of feed entries does not necessarily
    # change, but we still want to update the extra_state_attributes
    _attr_force_update = True

    def __init__(  # noqa: PLR0913, PLR0917  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self: FeedParserSensor,
        feed: str,
        name: str,
        date_format: str,
        show_topn: int,
        remove_summary_image: bool,
        exclusions: list[str | None],
        inclusions: list[str | None],
        scan_interval: timedelta,
        local_time: bool,
        user_agent: str = USER_AGENT,
    ) -> None:
        """Initialize the Feedparser sensor.

        Args:
            feed (str): URL of the feed (http, https or file).
            name (str): Name of the sensor.
            date_format (str): strftime format of the dates of the entries.
            show_topn (int): Maximum number of entries kept.
            remove_summary_image (bool): Whether to strip the <img> tags from the summary of the entries.
            exclusions (list[str | None]): Fields removed from the entries.
            inclusions (list[str | None]): Fields kept in the entries, all of them when empty.
            scan_interval (timedelta): Time between two updates of the feed.
            local_time (bool): Whether to convert the dates of the entries to the local time zone.
            user_agent (str): Value of the User-Agent header sent when fetching the feed.

        """
        self._feed = feed
        self._attr_name = name
        self._attr_icon = "mdi:rss"
        self._date_format = date_format
        self._show_topn: int = show_topn
        self._remove_summary_image = remove_summary_image
        self._inclusions = inclusions
        self._exclusions = exclusions
        self._scan_interval = scan_interval
        self._local_time = local_time
        self._user_agent = user_agent
        self._entries: list[dict[str, Any]] = []
        self._attr_extra_state_attributes = {"entries": self._entries}
        self._attr_attribution = "Data retrieved using RSS feedparser"
        _LOGGER.debug("Feed %s: FeedParserSensor initialized - %s", self.name, self)

    def __repr__(self: FeedParserSensor) -> str:
        """Return the representation.

        Returns:
            str: The name, feed URL and options of the sensor.

        """
        return (
            f'FeedParserSensor(name="{self.name}", feed="{self._feed}", '
            f"show_topn={self._show_topn}, "
            f"remove_summary_image={self._remove_summary_image}, "
            f"inclusions={self._inclusions}, "
            f"exclusions={self._exclusions}, scan_interval={self._scan_interval}, "
            f'local_time={self._local_time}, date_format="{self._date_format}", '
            f'user_agent="{self._user_agent}")'
        )

    def update(self: FeedParserSensor) -> None:
        """Parse the feed and update the state of the sensor."""
        _LOGGER.debug("Feed %s: Polling feed data from %s", self.name, self._feed)
        parsed_feed = FeedClient(self._user_agent).fetch(self._feed)

        if not parsed_feed.entries:
            self._attr_native_value = None
            _LOGGER.warning("Feed %s: No data received.", self.name)
            return

        _LOGGER.debug("Feed %s: Feed data fetched successfully", self.name)
        # set the sensor value to the amount of entries
        self._attr_native_value = min(len(parsed_feed.entries), self._show_topn)
        _LOGGER.debug(
            "Feed %s: %s entries is going to be added to the sensor",
            self.name,
            self.native_value,
        )
        self._entries.clear()  # clear the entries to avoid duplicates
        self._entries.extend(self._generate_entries(parsed_feed))
        _LOGGER.debug(
            "Feed %s: Sensor state updated - %s entries",
            self.name,
            len(self.feed_entries),
        )

    def _generate_entries(
        self: FeedParserSensor,
        parsed_feed: ParsedFeed,
    ) -> list[dict[str, Any]]:
        """Build the entries of the sensor from a parsed feed.

        Args:
            parsed_feed (ParsedFeed): The parsed feed.

        Returns:
            list[dict[str, Any]]: The first show_topn entries of the feed, as exposed by the sensor.

        """
        return [self._generate_sensor_entry(feed_entry) for feed_entry in parsed_feed.entries[: self._show_topn]]

    def _generate_sensor_entry(
        self: FeedParserSensor,
        feed_entry: FeedEntry,
    ) -> dict[str, Any]:
        """Build one entry of the sensor from an entry of the feed.

        Args:
            feed_entry (FeedEntry): Entry of the parsed feed.

        Returns:
            dict[str, Any]: The entry as exposed by the sensor, after inclusions, exclusions and conversions.

        """
        _LOGGER.debug("Feed %s: Generating sensor entry for %s", self.name, feed_entry)
        sensor_entry: dict[str, Any] = {}
        for key, value in feed_entry.items():
            if (self._inclusions and key not in self._inclusions) or ("parsed" in key) or (key in self._exclusions):
                continue
            if key in ["published", "updated", "created", "expired"]:
                parsed_date: datetime = self._parse_date(value)
                sensor_entry[key] = parsed_date.strftime(self._date_format)
            elif key == "image":
                sensor_entry["image"] = value.get("href")
            else:
                sensor_entry[key] = value

        if "image" in self._inclusions and "image" not in sensor_entry:
            sensor_entry["image"] = self._process_image(feed_entry)
        if (
            "link" in self._inclusions
            and "link" not in sensor_entry
            and (processed_link := self._process_link(feed_entry))
        ):
            sensor_entry["link"] = processed_link
        if self._remove_summary_image and "summary" in sensor_entry:
            sensor_entry["summary"] = re.sub(
                IMAGE_REGEX,
                "",
                sensor_entry["summary"],
            )
        _LOGGER.debug("Feed %s: Generated sensor entry: %s", self.name, sensor_entry)
        return sensor_entry

    def _parse_date(self: FeedParserSensor, date: str) -> datetime:
        """Parse a date of the feed.

        Args:
            date (str): Date as written in the feed.

        Returns:
            datetime: The date with a time zone, converted to the local time zone when local_time is set.

        Raises:
            ValueError: The date has no time zone and cannot be parsed.

        """
        try:
            parsed_time: datetime = email.utils.parsedate_to_datetime(date)
        except ValueError:
            _LOGGER.warning(
                (
                    "Feed %s: Unable to parse RFC-822 date from %s. "
                    "This could be caused by incorrect pubDate format "
                    "in the RSS feed or due to a leapp second"
                ),
                self.name,
                date,
            )
            # best effort to parse the date using dateutil
            parsed_time = parser.parse(date)

        if not parsed_time.tzinfo:
            # best effort to parse the date using dateutil
            parsed_time = parser.parse(date)
            if not parsed_time.tzinfo:
                msg = f"Feed {self.name}: Unable to parse date {date}, caused by an incorrect date format"
                raise ValueError(msg)
        if not parsed_time.tzname():
            # replace tzinfo with UTC offset if tzinfo does not contain a TZ name
            parsed_time = parsed_time.replace(
                tzinfo=timezone(parsed_time.utcoffset()),  # type: ignore[arg-type]
            )

        if self._local_time:
            parsed_time = dt.as_local(parsed_time)
        _LOGGER.debug("Feed %s: Parsed date: %s", self.name, parsed_time)
        return parsed_time

    def _process_image(self: FeedParserSensor, feed_entry: FeedEntry) -> str:
        """Return the image of a feed entry.

        Args:
            feed_entry (FeedEntry): Entry of the parsed feed.

        Returns:
            str: URL of the first image of the entry, or the default thumbnail when it has none.

        """
        image_url = find_image_url(feed_entry)
        if image_url is None:
            _LOGGER.debug(
                "Feed %s: Image is in inclusions, but no image was found for %s",
                self.name,
                feed_entry,
            )
            return DEFAULT_THUMBNAIL  # use default image if no image found
        return image_url

    def _process_link(self: FeedParserSensor, feed_entry: FeedEntry) -> str:
        """Return link from feed entry.

        Args:
            feed_entry (FeedEntry): Entry of the parsed feed.

        Returns:
            str: URL of the first link of the entry, or an empty string when it has none.

        """
        if len(feed_entry.get("links", ())) > 1:
            _LOGGER.debug(
                "Feed %s: More than one link found for %s. Using the first link.",
                self.name,
                feed_entry,
            )
        return find_link(feed_entry)

    @property
    def feed_entries(self: FeedParserSensor) -> list[dict[str, Any]]:
        """Return feed entries.

        Returns:
            list[dict[str, Any]]: Entries of the feed, as exposed by the sensor.

        """
        if hasattr(self, "_entries"):
            return self._entries
        return []

    @property
    def local_time(self: FeedParserSensor) -> bool:
        """Return local_time.

        Returns:
            bool: Whether the dates of the entries are converted to the local time zone.

        """
        return self._local_time

    @local_time.setter
    def local_time(self: FeedParserSensor, value: bool) -> None:
        """Set local_time.

        Args:
            value (bool): Whether to convert the dates of the entries to the local time zone.

        """
        self._local_time = value

    @property
    def extra_state_attributes(  # pyright: ignore[reportIncompatibleVariableOverride]
        self: FeedParserSensor,
    ) -> dict[str, list[dict[str, Any]]]:
        """Return entity specific state attributes.

        Returns:
            dict[str, list[dict[str, Any]]]: The entries of the feed, under the "entries" key.

        """
        return {"entries": self.feed_entries}
