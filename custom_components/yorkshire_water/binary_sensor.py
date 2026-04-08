"""Binary sensors for Yorkshire Water."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import YorkshireWaterDataUpdateCoordinator

BINARY_SENSOR_DESCRIPTIONS = [
    ("continuous_flow_alarm", "Continuous Flow Alarm", BinarySensorDeviceClass.PROBLEM, "continuousFlowAlarm"),
    ("estimated_consumption", "Estimated Consumption", BinarySensorDeviceClass.PROBLEM, "isEstimatedConsumption"),
    ("missing_consumption",   "Missing Consumption",   BinarySensorDeviceClass.PROBLEM, "isMissingConsumption"),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        YorkshireWaterBinarySensor(coordinator, entry, *desc)
        for desc in BINARY_SENSOR_DESCRIPTIONS
    )


class YorkshireWaterBinarySensor(CoordinatorEntity, BinarySensorEntity):
    def __init__(
        self,
        coordinator: YorkshireWaterDataUpdateCoordinator,
        entry: ConfigEntry,
        key: str,
        name: str,
        device_class: BinarySensorDeviceClass,
        api_field: str,
    ) -> None:
        super().__init__(coordinator)
        self._api_field = api_field
        self._attr_name = f"Yorkshire Water {name}"
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_class = device_class
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Yorkshire Water Smart Meter",
            manufacturer="Yorkshire Water",
            model="Smart Meter",
        )

    @property
    def is_on(self) -> bool | None:
        data = self.coordinator.data
        if not data:
            return None
        last_complete = data.get("last_complete_day")
        if last_complete is None:
            return None
        return bool(last_complete.get(self._api_field, False))

    @property
    def extra_state_attributes(self) -> dict:
        data = self.coordinator.data
        if not data:
            return {}
        day = data.get("last_complete_day") or {}
        return {"last_reading_date": day.get("date")}