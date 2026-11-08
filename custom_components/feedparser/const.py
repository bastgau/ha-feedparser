"""Constants for the Feedparser integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "feedparser"

CONF_FEED_URL = "feed_url"
CONF_DATE_FORMAT = "date_format"
CONF_LOCAL_TIME = "local_time"
CONF_INCLUSIONS = "inclusions"
CONF_EXCLUSIONS = "exclusions"
CONF_SHOW_TOPN = "show_topn"
CONF_REMOVE_SUMMARY_IMG = "remove_summary_image"
CONF_USER_AGENT = "user_agent"

DEFAULT_DATE_FORMAT = "%a, %b %d %I:%M %p"
DEFAULT_LOCAL_TIME = False
DEFAULT_REMOVE_SUMMARY_IMG = False
DEFAULT_SCAN_INTERVAL = timedelta(hours=1)
DEFAULT_THUMBNAIL = "https://www.home-assistant.io/images/favicon-192x192-full.png"
DEFAULT_TOPN = 9999
USER_AGENT = "Home Assistant Feed-parser Integration"

# Schemes accepted for a feed URL: file is what the tests and local feeds use.
SUPPORTED_URL_SCHEMES = ("http", "https", "file")
