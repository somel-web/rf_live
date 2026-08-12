"""Entités sensor RF Live : émission en cours et émission suivante."""
from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
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

    async_add_entities(
        [
            RFLiveStepSensor(coordinator, entry, key="current", label="En cours"),
            RFLiveStepSensor(coordinator, entry, key="next", label="Suivant"),
        ]
    )


class RFLiveStepSensor(CoordinatorEntity[RFLiveUpdateCoordinator], SensorEntity):
    """Sensor exposant les infos d'un step (courant ou suivant)."""

    _attr_icon = "mdi:radio"
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: RFLiveUpdateCoordinator,
        entry: ConfigEntry,
        key: str,
        label: str,
    ) -> None:
        super().__init__(coordinator)
        self._key = key
        self._attr_name = label
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=coordinator.channel_name,
            manufacturer="Radio France",
            model=entry.data.get(CONF_CHANNEL),
        )

    @property
    def _step_data(self) -> dict[str, Any] | None:
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get(self._key)

    @property
    def native_value(self) -> str | None:
        step = self._step_data
        if not step:
            return None
        return step.get("title")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        step = self._step_data

        attrs: dict[str, Any] = {
            "stream_url": self.coordinator.stream_url,
            "image_generique": self.coordinator.generic_image,
        }

        if step:
            attrs.update(
                {
                    "nom_emission": step.get("nom_emission"),
                    "description": step.get("description"),
                    "image": step.get("image"),
                    "image_banner": step.get("image_banner"),
                    "debut": step.get("debut"),
                    "fin": step.get("fin"),
                }
            )

        return attrs
