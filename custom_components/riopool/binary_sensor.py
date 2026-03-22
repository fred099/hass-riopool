"""Binary sensor entities for Riopool Rio750 Pool Pump fault codes."""

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

FAULT_SENSORS = [
    ("TP", "Temperature Protection", "Motortemperatur >90°C eller <-5°C"),
    ("BP", "Blocking Protection", "Motor eller pumphjul blockerat"),
    ("OL", "Overload Protection", "Överlast / för hög ström"),
    ("LP", "Phase Loss Protection", "Fasförlust"),
    ("CP", "Communication Loss", "Kommunikationsfel mellan display och huvudkort"),
]


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    """Set up Riopool binary sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    entities = [
        RiopoolFaultSensor(coordinator, entry, key, name, desc)
        for key, name, desc in FAULT_SENSORS
    ]
    async_add_entities(entities)


class RiopoolFaultSensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor for pump fault indicators."""

    def __init__(self, coordinator, entry, key, name, description):
        super().__init__(coordinator)
        self._key = key
        self._attr_name = f"Rio750 Fault: {name}"
        self._attr_unique_id = f"riopool_{entry.data['host']}_fault_{key}"
        self._attr_device_class = BinarySensorDeviceClass.PROBLEM
        self._attr_icon = "mdi:alert-circle"
        self._attr_entity_registry_enabled_default = True
        self._description = description
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.data["host"])},
            "name": "Riopool Rio750",
            "manufacturer": "Starmatrix / Riopool",
            "model": "Rio750 Inverter WiFi BT",
        }

    @property
    def is_on(self):
        if self.coordinator.data:
            return self.coordinator.data.get(self._key, False)
        return False

    @property
    def extra_state_attributes(self):
        return {"description": self._description}
