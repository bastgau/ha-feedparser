"""Generate Home Assistant sensors config from test feeds."""
from tests.feedparser.constants import TEST_FEEDS
from tests.feedparser.feedsource import FeedSource

fsources = [FeedSource(fs) for fs in TEST_FEEDS]
FeedSource.create_ha_sensors_config_file(fsources)
