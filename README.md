# sensor.feedparser

RSS feed custom component for [Home Assistant](https://www.home-assistant.io/) which can be used in conjunction with the custom [Lovelace](https://www.home-assistant.io/lovelace) [list-card](https://github.com/custom-cards/list-card)

[![Maintainer: bastgau](https://img.shields.io/badge/maintainer-bastgau-orange?logo=github&logoColor=%23959da5&labelColor=%232d333a)](https://github.com/bastgau)
[![Made with Python](https://img.shields.io/badge/Made_with-Python-blue?style=flat&logo=python&logoColor=%23959da5&labelColor=%232d333a)](https://www.python.org/)
[![Made for Home Assistant](https://img.shields.io/badge/Made_for-Homeassistant-blue?style=flat&logo=homeassistant&logoColor=%23959da5&labelColor=%232d333a)](https://www.home-assistant.io/)
[![GitHub Release](https://img.shields.io/github/v/release/bastgau/ha-feedparser?logo=github&logoColor=%23959da5&labelColor=%232d333a&color=%230e80c0)](https://github.com/bastgau/ha-feedparser/releases)
[![HACS validation](https://github.com/bastgau/ha-feedparser/actions/workflows/validate-for-hacs.yml/badge.svg)](https://github.com/bastgau/ha-feedparser/actions/workflows/validate-for-hacs.yml)
[![HASSFEST validation](https://github.com/bastgau/ha-feedparser/actions/workflows/validate-with-hassfest.yml/badge.svg)](https://github.com/bastgau/ha-feedparser/actions/workflows/validate-with-hassfest.yml)

## About this fork

This project is a fork of [custom-components/feedparser](https://github.com/custom-components/feedparser), the RSS feed integration for Home Assistant created by [Ian Richardson](https://github.com/iantrich) and developed since then by [Ondřej Gajdušek](https://github.com/ogajduse) and the other contributors of the original project.

A big thank you to all of them: the idea, the design and the vast majority of the code are theirs, and this fork would not exist without their work. The original MIT license and its copyright notice are kept unchanged.

This fork is maintained by [Bastien Gautier](https://github.com/bastgau). It stays based on the original code and currently adds:

- a `user_agent` option, to send a browser User-Agent to servers that block or stall unknown clients (a contribution of [Dave Nicoll](https://github.com/davenicoll));
- images read from `media:content` elements, which is handy for Mastodon feeds (a contribution of [Piotr Gaczkowski](https://github.com/DoomHammer));
- a small typed wrapper around `feedparser`, a reorganised test suite and strict linting.

Both contributions were first proposed to the original repository, and their authors' names are kept in the Git history. If you run into a problem that also exists in the original project, feel free to report it there too.

## Support

If you encounter any issues or wish to contribute to improving this integration, feel free to open an issue or a pull request on the GitHub repository.

[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/bastgau)

## Installation

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

1. Open HACS Settings and add this repository (https://github.com/bastgau/ha-feedparser/)
   as a Custom Repository (use **Integration** as the category).
2. The `feedparser` page should automatically load (or find it in the HACS Store)
3. Click `Install`

Alternatively, click on the button below to add the repository:

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?category=Integration&repository=ha-feedparser&owner=bastgau)

## Configuration

**Example configuration.yaml:**

```yaml
sensor:
  - platform: feedparser
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
  - platform: feedparser
    name: Algemeen
    feed_url: https://www.nu.nl/rss/Algemeen
    local_time: true
    show_topn: 1

  # Some servers block or stall unknown clients; send a browser User-Agent instead
  - platform: feedparser
    name: Picky Server Feed
    feed_url: https://example.com/rss
    user_agent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
```

If you wish the integration to look for enclosures in the feed entries, add `image` to `inclusions` list. Do not use `enclosure`.
The integration tries to get the link to an image for the given feed item and stores it under the attribute named `image`. If it fails to find it, it assigns the Home Assistant logo to it instead.

Note that the original `pubDate` field is available under `published` attribute for the given feed entry. Other date-type values that can be available are `updated`, `created` and `expired`. Please refer to [the documentation of the original feedparser](https://feedparser.readthedocs.io/en/latest/date-parsing.html) library.

**Configuration variables:**

| key                          | description                                                                                                  |
| :--------------------------- | :----------------------------------------------------------------------------------------------------------- |
| **platform (Required)**      | The platform name                                                                                            |
| **name (Required)**          | Name your feed                                                                                               |
| **feed_url (Required)**      | The RSS feed URL                                                                                             |
| **date_format (Optional)**   | strftime date format for date strings **Default** `%a, %b %d %I:%M %p`                                       |
| **local_time (Optional)**    | Whether to convert date into local time **Default** false                                                    |
| **show_topn (Optional)**     | fetch how many entres from rss source，if not set then fetch all                                             |
| **inclusions (Optional)**    | List of fields to include from populating the list                                                           |
| **exclusions (Optional)**    | List of fields to exclude from populating the list                                                           |
| **scan_interval (Optional)** | Update interval in hours                                                                                     |
| **user_agent (Optional)**    | User-Agent header sent when fetching the feed **Default** `Home Assistant Feed-parser Integration <version>` |

---

Note: Will return all fields if no inclusions or exclusions are specified

Due to how `custom_components` are loaded, it is normal to see a `ModuleNotFoundError` error on first boot after adding this, to resolve it, restart Home-Assistant.
