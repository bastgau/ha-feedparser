"""A component which allows you to parse an RSS feed into a sensor.

For more details about this component, please refer to the documentation at
https://github.com/bastgau/ha-feedparser

Following spec from https://validator.w3.org/feed/docs/rss2.html
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.const import Platform

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Feedparser from a config entry.

    Args:
        hass (HomeAssistant): The Home Assistant instance.
        entry (ConfigEntry): The config entry to set up.

    Returns:
        bool: True if setup succeeded.

    """
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry.

    Args:
        hass (HomeAssistant): The Home Assistant instance.
        entry (ConfigEntry): The config entry to unload.

    Returns:
        bool: True if the platforms were unloaded.

    """
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
