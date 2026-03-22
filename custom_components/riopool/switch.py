"""Switch entities for Riopool Rio750 Pool Pump."""

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    """Set up Riopool switches."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    entities = [
        RiopoolSwitch(coordinator, entry, "ManualSwitch", "Pump", "mdi:pump"),
    ]
    async_add_entities(entities)


class RiopoolSwitch(CoordinatorEntity, SwitchEntity):
    """Switch for Riopool pump on/off."""

    def __init__(self, coordinator, entry, key, name, icon):
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
    def is_on(self):
        if self.coordinator.data:
            return self.coordinator.data.get(self._key, False)
        return False

    async def async_turn_on(self, **kwargs):
        await self.coordinator.async_send_control({self._key: True})

    async def async_turn_off(self, **kwargs):
        await self.coordinator.async_send_control({self._key: False})
