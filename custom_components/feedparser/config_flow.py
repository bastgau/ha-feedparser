"""Config flow for the Feedparser integration (one config entry per feed)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast
from urllib.parse import urlsplit

import probatio
import requests

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlowWithReload
from homeassistant.const import CONF_NAME, CONF_SCAN_INTERVAL
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    BooleanSelector,  # pyright: ignore[reportUnknownVariableType]
    DurationSelector,  # pyright: ignore[reportUnknownVariableType]
    DurationSelectorConfig,
    NumberSelector,  # pyright: ignore[reportUnknownVariableType]
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,  # pyright: ignore[reportUnknownVariableType]
    TextSelectorConfig,
)

from .const import (
    CONF_DATE_FORMAT,
    CONF_EXCLUSIONS,
    CONF_FEED_URL,
    CONF_INCLUSIONS,
    CONF_LOCAL_TIME,
    CONF_REMOVE_SUMMARY_IMG,
    CONF_SHOW_TOPN,
    CONF_USER_AGENT,
    DEFAULT_DATE_FORMAT,
    DEFAULT_LOCAL_TIME,
    DEFAULT_REMOVE_SUMMARY_IMG,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TOPN,
    DOMAIN,
    SUPPORTED_URL_SCHEMES,
    USER_AGENT,
)
from .feedparser_wrapper import FeedClient

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

# Shortest refresh interval accepted: polling a feed more often than once a minute is never useful.
MIN_SCAN_INTERVAL_SECONDS = 60

# Units of the interval stored by the duration selector, with their length in seconds.
SECONDS_PER_UNIT = {"days": 86400, "hours": 3600, "minutes": 60, "seconds": 1}


def _default_scan_interval() -> dict[str, int]:
    """Return the default scan interval in the shape stored by the duration selector.

    Returns:
        dict[str, int]: The default interval as hours, minutes and seconds.

    """
    seconds = int(DEFAULT_SCAN_INTERVAL.total_seconds())
    return {"hours": seconds // 3600, "minutes": seconds % 3600 // 60, "seconds": seconds % 60}


def _interval_seconds(interval: object) -> float:
    """Compute the length of an interval stored by the duration selector.

    Args:
        interval (object): Mapping such as {"hours": 1, "minutes": 30, "seconds": 0}.

    Returns:
        float: The length of the interval in seconds, 0 when it is not a mapping.

    """
    if not isinstance(interval, dict):
        return 0
    values = cast("dict[str, float]", interval)
    return float(sum(factor * values.get(unit, 0) for unit, factor in SECONDS_PER_UNIT.items()))


def _options_schema(options: dict[str, Any]) -> dict[Any, Any]:
    """Build the form fields shared by the setup form and the options form.

    Args:
        options (dict[str, Any]): Current values of the options, used as defaults of the form.

    Returns:
        dict[Any, Any]: The fields of the form, to be spread into a probatio.Schema mapping.

    """
    return {
        probatio.Required(CONF_DATE_FORMAT, default=options.get(CONF_DATE_FORMAT, DEFAULT_DATE_FORMAT)): TextSelector(),
        probatio.Required(CONF_LOCAL_TIME, default=options.get(CONF_LOCAL_TIME, DEFAULT_LOCAL_TIME)): BooleanSelector(),
        probatio.Required(
            CONF_SCAN_INTERVAL, default=options.get(CONF_SCAN_INTERVAL, _default_scan_interval())
        ): DurationSelector(DurationSelectorConfig(allow_negative=False)),
        probatio.Required(CONF_SHOW_TOPN, default=options.get(CONF_SHOW_TOPN, DEFAULT_TOPN)): NumberSelector(
            NumberSelectorConfig(min=1, step=1, mode=NumberSelectorMode.BOX)
        ),
        probatio.Required(
            CONF_REMOVE_SUMMARY_IMG, default=options.get(CONF_REMOVE_SUMMARY_IMG, DEFAULT_REMOVE_SUMMARY_IMG)
        ): BooleanSelector(),
        probatio.Optional(CONF_INCLUSIONS, default=options.get(CONF_INCLUSIONS, [])): TextSelector(
            TextSelectorConfig(multiple=True)
        ),
        probatio.Optional(CONF_EXCLUSIONS, default=options.get(CONF_EXCLUSIONS, [])): TextSelector(
            TextSelectorConfig(multiple=True)
        ),
        probatio.Required(CONF_USER_AGENT, default=options.get(CONF_USER_AGENT, USER_AGENT)): TextSelector(),
    }


def _normalize_options(user_input: dict[str, Any]) -> dict[str, Any]:
    """Turn the options submitted by a form into the values stored in the config entry.

    Args:
        user_input (dict[str, Any]): Values submitted by the setup or options form.

    Returns:
        dict[str, Any]: The options to store, with the number of entries as an integer.

    """
    return {
        CONF_DATE_FORMAT: user_input[CONF_DATE_FORMAT],
        CONF_LOCAL_TIME: user_input[CONF_LOCAL_TIME],
        CONF_SCAN_INTERVAL: user_input[CONF_SCAN_INTERVAL],
        CONF_SHOW_TOPN: int(user_input[CONF_SHOW_TOPN]),
        CONF_REMOVE_SUMMARY_IMG: user_input[CONF_REMOVE_SUMMARY_IMG],
        CONF_INCLUSIONS: list(user_input.get(CONF_INCLUSIONS, [])),
        CONF_EXCLUSIONS: list(user_input.get(CONF_EXCLUSIONS, [])),
        CONF_USER_AGENT: user_input[CONF_USER_AGENT],
    }


def _validate_scan_interval(user_input: dict[str, Any], errors: dict[str, str]) -> None:
    """Record an error when the refresh interval is shorter than the minimum.

    Args:
        user_input (dict[str, Any]): Values submitted by the setup or options form.
        errors (dict[str, str]): Errors of the form, completed in place.

    """
    if _interval_seconds(user_input[CONF_SCAN_INTERVAL]) < MIN_SCAN_INTERVAL_SECONDS:
        errors[CONF_SCAN_INTERVAL] = "scan_interval_too_short"


class FeedparserConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the config flow: each config entry follows one feed."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> FeedparserOptionsFlow:  # noqa: ARG004
        """Return the options flow of a config entry.

        Args:
            config_entry (ConfigEntry): The config entry whose options are edited, unused.

        Returns:
            FeedparserOptionsFlow: The options flow.

        """
        return FeedparserOptionsFlow()

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Ask for the feed and its settings, then create the config entry.

        Args:
            user_input (dict[str, Any] | None): Form data, or None to show the form.

        Returns:
            ConfigFlowResult: The created entry, or the form with its errors.

        """
        errors: dict[str, str] = {}
        defaults: dict[str, Any] = {}

        if user_input is not None:
            defaults = user_input
            feed_url = str(user_input[CONF_FEED_URL]).strip()
            _validate_scan_interval(user_input, errors)
            if urlsplit(feed_url).scheme not in SUPPORTED_URL_SCHEMES:
                errors[CONF_FEED_URL] = "invalid_url"

            if not errors:
                await self.async_set_unique_id(feed_url)
                self._abort_if_unique_id_configured()
                try:
                    await self.hass.async_add_executor_job(FeedClient(user_input[CONF_USER_AGENT]).fetch, feed_url)
                except requests.RequestException:
                    errors["base"] = "cannot_connect"
                else:
                    return self.async_create_entry(
                        title=str(user_input[CONF_NAME]).strip(),
                        data={CONF_NAME: str(user_input[CONF_NAME]).strip(), CONF_FEED_URL: feed_url},
                        options=_normalize_options(user_input),
                    )

        schema = probatio.Schema(
            {
                probatio.Required(CONF_NAME, default=defaults.get(CONF_NAME, probatio.UNDEFINED)): TextSelector(),
                probatio.Required(
                    CONF_FEED_URL, default=defaults.get(CONF_FEED_URL, probatio.UNDEFINED)
                ): TextSelector(),
                **_options_schema(defaults),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)


class FeedparserOptionsFlow(OptionsFlowWithReload):
    """Edit the settings of a feed; saving them reloads the config entry."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Let the user edit the settings of the feed.

        Args:
            user_input (dict[str, Any] | None): Form data, or None to show the form.

        Returns:
            ConfigFlowResult: The saved options, or the form with its errors.

        """
        errors: dict[str, str] = {}

        if user_input is not None:
            _validate_scan_interval(user_input, errors)
            if not errors:
                return self.async_create_entry(data=_normalize_options(user_input))

        current = user_input if user_input is not None else {**self.config_entry.options}
        return self.async_show_form(
            step_id="init", data_schema=probatio.Schema(_options_schema(current)), errors=errors
        )
