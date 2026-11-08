# ha-feedparser

📰 The Feedparser integration for [Home Assistant](https://www.home-assistant.io/) turns RSS and Atom feeds into sensors, directly from Home Assistant.

[![Maintainer: bastgau](https://img.shields.io/badge/maintainer-bastgau-orange?logo=github&logoColor=%23959da5&labelColor=%232d333a)](https://github.com/bastgau)
[![Made with Python](https://img.shields.io/badge/Made_with-Python-blue?style=flat&logo=python&logoColor=%23959da5&labelColor=%232d333a)](https://www.python.org/)
[![Made for Home Assistant](https://img.shields.io/badge/Made_for-Homeassistant-blue?style=flat&logo=homeassistant&logoColor=%23959da5&labelColor=%232d333a)](https://www.home-assistant.io/)
[![GitHub Release](https://img.shields.io/github/v/release/bastgau/ha-feedparser?logo=github&logoColor=%23959da5&labelColor=%232d333a&color=%230e80c0)](https://github.com/bastgau/ha-feedparser/releases)
[![HACS validation](https://github.com/bastgau/ha-feedparser/actions/workflows/validate-for-hacs.yml/badge.svg)](https://github.com/bastgau/ha-feedparser/actions/workflows/validate-for-hacs.yml)
[![HASSFEST validation](https://github.com/bastgau/ha-feedparser/actions/workflows/validate-with-hassfest.yml/badge.svg)](https://github.com/bastgau/ha-feedparser/actions/workflows/validate-with-hassfest.yml)

## Installation

### Installation via HACS

1. Add this repository as a custom repository to HACS:

[![Add Repository](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=bastgau&repository=ha-feedparser&category=Integration)

2. Use HACS to install the integration.
3. Restart Home Assistant.
4. Set up the integration using the UI:

[![Add Integration](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=rss_feedparser)

### Manual Installation

1. Download the integration files from the GitHub repository.
2. Place the `rss_feedparser` folder in the `custom_components` directory of Home Assistant.
3. Restart Home Assistant.
4. Set up the integration using the UI:

[![Add Integration](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=rss_feedparser)

## Configuration

### UI configuration (recommended)

1. Go to **Settings** → **Devices & services** and click **Add integration**.
2. Search for **RSS Feedparser**.
3. Enter a name and the URL of the feed, then adjust the settings if you need to. The feed is fetched once to check that it can be read.

Add the integration once per feed. To change the settings later, open the integration and click **Configure**: saving them reloads that feed.

The settings are the ones listed in [Configuration variables](#configuration-variables). In the UI, `inclusions` and `exclusions` are lists of fields, and the refresh interval is set with a duration (at least one minute).

### YAML configuration

The sensor can still be configured in YAML.

> [!NOTE]
> Coming from the original integration? This fork has its own name, `rss_feedparser`, so both can be installed side by side. To switch, replace `platform: feedparser` with `platform: rss_feedparser` in your configuration.

**Example configuration.yaml:**

```yaml
sensor:
  - platform: rss_feedparser
    name: Engineering Feed
    feed_url: "https://www.sciencedaily.com/rss/matter_energy/engineering.xml"
    date_format: "%a, %d %b %Y %H:%M:%S %Z"
    scan_interval:
      hours: 3
    inclusions:
      - title
      - link
      - description
      - image
      - published
    exclusions:
      - language

  # Configuration of the second sensor tracking a different RSS feed
  - platform: rss_feedparser
    name: Algemeen
    feed_url: https://www.nu.nl/rss/Algemeen
    local_time: true
    show_topn: 1

  # Some servers block or stall unknown clients; send a browser User-Agent instead
  - platform: rss_feedparser
    name: Picky Server Feed
    feed_url: https://example.com/rss
    user_agent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
```

If you wish the integration to look for enclosures in the feed entries, add `image` to `inclusions` list. Do not use `enclosure`.
The integration tries to get the link to an image for the given feed item and stores it under the attribute named `image`. If it fails to find it, it assigns the Home Assistant logo to it instead.

Note that the original `pubDate` field is available under `published` attribute for the given feed entry. Other date-type values that can be available are `updated`, `created` and `expired`. Please refer to [the documentation of the original feedparser](https://feedparser.readthedocs.io/en/latest/date-parsing.html) library.

### Configuration variables

| key                          | description                                                                                        |
| :--------------------------- | :------------------------------------------------------------------------------------------------- |
| **platform (Required)**      | The platform name                                                                                  |
| **name (Required)**          | Name your feed                                                                                     |
| **feed_url (Required)**      | The RSS feed URL                                                                                   |
| **date_format (Optional)**   | strftime date format for date strings **Default** `%a, %b %d %I:%M %p`                             |
| **local_time (Optional)**    | Whether to convert date into local time **Default** false                                          |
| **show_topn (Optional)**     | fetch how many entres from rss source，if not set then fetch all                                   |
| **inclusions (Optional)**    | List of fields to include from populating the list                                                 |
| **exclusions (Optional)**    | List of fields to exclude from populating the list                                                 |
| **scan_interval (Optional)** | Update interval in hours                                                                           |
| **user_agent (Optional)**    | User-Agent header sent when fetching the feed **Default** `Home Assistant Feed-parser Integration` |

---

Note: Will return all fields if no inclusions or exclusions are specified

Due to how `custom_components` are loaded, it is normal to see a `ModuleNotFoundError` error on first boot after adding this, to resolve it, restart Home-Assistant.

## Support

If you encounter any issues or wish to contribute to improving this integration, feel free to open an issue or a pull request on the GitHub repository.

[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/bastgau)

## About this fork

This project is a fork of [custom-components/feedparser](https://github.com/custom-components/feedparser), the RSS feed integration for Home Assistant created by [Ian Richardson](https://github.com/iantrich) and developed since then by [Ondřej Gajdušek](https://github.com/ogajduse) and the other contributors of the original project.

A big thank you to all of them: the idea, the design and the vast majority of the code are theirs, and this fork would not exist without their work. The original MIT license and its copyright notice are kept unchanged.

This fork is maintained by [bastgau](https://github.com/bastgau). It has its own integration name (`rss_feedparser`), so it can run next to the original. It stays based on the original code and currently adds:

- a `user_agent` option, to send a browser User-Agent to servers that block or stall unknown clients (a contribution of [Dave Nicoll](https://github.com/davenicoll));
- images read from `media:content` elements, which is handy for Mastodon feeds (a contribution of [Piotr Gaczkowski](https://github.com/DoomHammer));
- a small typed wrapper around `feedparser`, a reorganised test suite and strict linting.

Both contributions were first proposed to the original repository, and their authors' names are kept in the Git history. If you run into a problem that also exists in the original project, feel free to report it there too.
