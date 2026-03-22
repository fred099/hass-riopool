"""Number entities for Riopool Rio750 Pool Pump."""

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    SPEED_RATIO,
    SPEED_RPM_MIN,
    SPEED_RPM_MAX,
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    """Set up Riopool number entities."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    entities = [
        RiopoolSpeedNumber(
            coordinator, entry, "ManualSetSpeed", "Manual Speed",
        ),
    ]
    async_add_entities(entities)


class RiopoolSpeedNumber(CoordinatorEntity, NumberEntity):
    """Number entity for pump speed (RPM)."""

    def __init__(self, coordinator, entry, key, name):
        super().__init__(coordinator)
        self._key = key
        self._attr_name = f"Rio750 {name}"
        self._attr_unique_id = f"riopool_{entry.data['host']}_{key}"
        self._attr_icon = "mdi:speedometer"
        self._attr_native_min_value = SPEED_RPM_MIN
        self._attr_native_max_value = SPEED_RPM_MAX
        self._attr_native_step = SPEED_RATIO
        self._attr_native_unit_of_measurement = "RPM"
        self._attr_mode = NumberMode.SLIDER
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.data["host"])},
            "name": "Riopool Rio750",
            "manufacturer": "Starmatrix / Riopool",
            "model": "Rio750 Inverter WiFi BT",
        }

    @property
    def native_value(self):
        if self.coordinator.data:
            raw = self.coordinator.data.get(self._key)
            if raw is not None:
                return raw * SPEED_RATIO
        return None

    async def async_set_native_value(self, value: float):
        raw = int(value / SPEED_RATIO)
        await self.coordinator.async_send_control({self._key: raw})
