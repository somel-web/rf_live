"""Intégration RF Live : infos "now playing" des chaînes Radio France."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import (
    CHANNELS,
    CONF_CHANNEL,
    CONF_GENERIC_IMAGE,
    CONF_IMAGE_RESOLUTION,
    CONF_STREAM_URL,
    DEFAULT_IMAGE_RESOLUTION,
    DOMAIN,
)
from .coordinator import RFLiveUpdateCoordinator

PLATFORMS = ["sensor", "button"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    data = {**entry.data, **entry.options}

    channel_id = data[CONF_CHANNEL]
    channel_name = CHANNELS.get(channel_id, channel_id)

    coordinator = RFLiveUpdateCoordinator(
        hass,
        channel_id=channel_id,
        channel_name=channel_name,
        stream_url=data[CONF_STREAM_URL],
        generic_image=data[CONF_GENERIC_IMAGE],
        resolution=data.get(CONF_IMAGE_RESOLUTION, DEFAULT_IMAGE_RESOLUTION),
    )

    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:  # noqa: BLE001
        raise ConfigEntryNotReady(
            f"Impossible de joindre l'API Radio France pour {channel_name}"
        ) from err

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unloaded


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Recharge l'entry quand les options (URL flux, image, résolution) changent."""
    await hass.config_entries.async_reload(entry.entry_id)
