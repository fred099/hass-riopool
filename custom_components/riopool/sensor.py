"""Sensor entities for Riopool Rio750 Pool Pump."""

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUAL_GEARS, MODES


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    """Set up Riopool sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    entities = [
        RiopoolSpeedSensor(coordinator, entry),
        RiopoolPowerSensor(coordinator, entry),
        RiopoolEnergySavingSensor(coordinator, entry),
        RiopoolModeSensor(coordinator, entry),
        RiopoolGearSensor(coordinator, entry),
    ]
    async_add_entities(entities)


class RiopoolBaseSensor(CoordinatorEntity, SensorEntity):
    """Base class for Riopool sensors."""

    def __init__(self, coordinator, entry, key, name, icon=None):
        super().__init__(coordinator)
        self._key = key
        self._attr_name = f"Rio750 {name}"
        self._attr_unique_id = f"riopool_{entry.data['host']}_{key}"
        self._attr_icon = icon
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.data["host"])},
            "name": "Riopool Rio750",
            "manufacturer": "Starmatrix / Riopool",
            "model": "Rio750 Inverter WiFi BT",
        }

    @property
    def native_value(self):
        if self.coordinator.data:
            return self.coordinator.data.get(self._key)
        return None


class RiopoolSpeedSensor(RiopoolBaseSensor):
    """Sensor for current pump speed in RPM."""

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "RealtimeSpeed", "Speed", "mdi:speedometer")
        self._attr_native_unit_of_measurement = "RPM"
        self._attr_state_class = SensorStateClass.MEASUREMENT


class RiopoolPowerSensor(RiopoolBaseSensor):
    """Sensor for current power consumption."""

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Power", "Power", "mdi:flash")
        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = SensorStateClass.MEASUREMENT


class RiopoolEnergySavingSensor(RiopoolBaseSensor):
    """Sensor for energy saving ratio."""

    def __init__(self, coordinator, entry):
        super().__init__(
            coordinator, entry, "EnergySavingRatio", "Energy Saving", "mdi:leaf"
        )
        self._attr_native_unit_of_measurement = "%"
        self._attr_state_class = SensorStateClass.MEASUREMENT


class RiopoolModeSensor(RiopoolBaseSensor):
    """Sensor for current pump mode (read-only)."""

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Mode", "Mode", "mdi:cog")


class RiopoolGearSensor(RiopoolBaseSensor):
    """Sensor for current manual gear (read-only)."""

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "ManualGear", "Manual Gear", "mdi:speedometer")
