"""Config flow pour RF Live."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    CHANNELS,
    CONF_CHANNEL,
    CONF_GENERIC_IMAGE,
    CONF_IMAGE_RESOLUTION,
    CONF_STREAM_URL,
    DEFAULT_IMAGE_RESOLUTION,
    DOMAIN,
)


def _channel_options() -> list[dict[str, str]]:
    return [
        {"value": channel_id, "label": name}
        for channel_id, name in CHANNELS.items()
    ]


class RFLiveConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Gère la configuration d'une instance RF Live (= une chaîne)."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            channel_id = user_input[CONF_CHANNEL]

            # Une seule instance par chaîne.
            await self.async_set_unique_id(channel_id)
            self._abort_if_unique_id_configured()

            stream_url = user_input[CONF_STREAM_URL].strip()
            generic_image = user_input[CONF_GENERIC_IMAGE].strip()

            if not stream_url.startswith(("http://", "https://")):
                errors[CONF_STREAM_URL] = "invalid_url"
            elif not generic_image.startswith(("http://", "https://")):
                errors[CONF_GENERIC_IMAGE] = "invalid_url"
            else:
                return self.async_create_entry(
                    title=CHANNELS[channel_id],
                    data={
                        CONF_CHANNEL: channel_id,
                        CONF_STREAM_URL: stream_url,
                        CONF_GENERIC_IMAGE: generic_image,
                        CONF_IMAGE_RESOLUTION: user_input[CONF_IMAGE_RESOLUTION].strip()
                        or DEFAULT_IMAGE_RESOLUTION,
                    },
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_CHANNEL): SelectSelector(
                    SelectSelectorConfig(
                        options=_channel_options(),
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Required(CONF_STREAM_URL): str,
                vol.Required(CONF_GENERIC_IMAGE): str,
                vol.Optional(
                    CONF_IMAGE_RESOLUTION, default=DEFAULT_IMAGE_RESOLUTION
                ): str,
            }
        )

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> RFLiveOptionsFlow:
        return RFLiveOptionsFlow(config_entry)


class RFLiveOptionsFlow(config_entries.OptionsFlow):
    """Permet de modifier l'URL du flux, l'image générique et la résolution après coup."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}
        current = {**self._entry.data, **self._entry.options}

        if user_input is not None:
            stream_url = user_input[CONF_STREAM_URL].strip()
            generic_image = user_input[CONF_GENERIC_IMAGE].strip()

            if not stream_url.startswith(("http://", "https://")):
                errors[CONF_STREAM_URL] = "invalid_url"
            elif not generic_image.startswith(("http://", "https://")):
                errors[CONF_GENERIC_IMAGE] = "invalid_url"
            else:
                return self.async_create_entry(
                    title="",
                    data={
                        CONF_STREAM_URL: stream_url,
                        CONF_GENERIC_IMAGE: generic_image,
                        CONF_IMAGE_RESOLUTION: user_input[CONF_IMAGE_RESOLUTION].strip()
                        or DEFAULT_IMAGE_RESOLUTION,
                    },
                )

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_STREAM_URL, default=current.get(CONF_STREAM_URL, "")
                ): str,
                vol.Required(
                    CONF_GENERIC_IMAGE, default=current.get(CONF_GENERIC_IMAGE, "")
                ): str,
                vol.Optional(
                    CONF_IMAGE_RESOLUTION,
                    default=current.get(
                        CONF_IMAGE_RESOLUTION, DEFAULT_IMAGE_RESOLUTION
                    ),
                ): str,
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)
