"""Entité button RF Live : force un refresh immédiat du coordinator."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_CHANNEL, DOMAIN
from .coordinator import RFLiveUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: RFLiveUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([RFLiveForceRefreshButton(coordinator, entry)])


class RFLiveForceRefreshButton(CoordinatorEntity[RFLiveUpdateCoordinator], ButtonEntity):
    """Bouton qui force un fetch immédiat, hors du reschedule dynamique."""

    _attr_icon = "mdi:refresh"
    _attr_has_entity_name = True

    def __init__(self, coordinator: RFLiveUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_name = "Forcer la mise à jour"
        self._attr_unique_id = f"{entry.entry_id}_force_refresh"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=coordinator.channel_name,
            manufacturer="Radio France",
            model=entry.data.get(CONF_CHANNEL),
        )

    async def async_press(self) -> None:
        # request_refresh (pas async_refresh) : passe par le debouncer du
        # coordinator, évite les appels API en rafale si le bouton est
        # pressé plusieurs fois rapidement.
        await self.coordinator.async_request_refresh()
