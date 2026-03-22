"""Riopool Rio750 Pool Pump integration for Home Assistant."""

import asyncio
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, PLATFORMS, UPDATE_INTERVAL, LOGGER
from .gizwits_lan import GizwitsLanClient


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Riopool component."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Riopool from a config entry."""
    host = entry.data["host"]
    client = GizwitsLanClient(host)

    coordinator = RiopoolDataUpdateCoordinator(hass, client, host)

    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:
        await client.disconnect()
        raise ConfigEntryNotReady(f"Failed to connect to pump at {host}") from err

    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "client": client,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        data = hass.data[DOMAIN].pop(entry.entry_id)
        await data["client"].disconnect()
    return unload_ok


class RiopoolDataUpdateCoordinator(DataUpdateCoordinator):
    """Coordinator to manage polling the pool pump."""

    def __init__(self, hass: HomeAssistant, client: GizwitsLanClient, host: str):
        super().__init__(
            hass,
            LOGGER,
            name=f"Riopool {host}",
            update_interval=UPDATE_INTERVAL,
        )
        self.client = client
        self._host = host

    async def _async_update_data(self) -> dict:
        """Fetch data from the pump."""
        try:
            data = await self.client.read_status()
            if data is None:
                raise UpdateFailed(f"Failed to read status from {self._host}")
            return data
        except Exception as err:
            raise UpdateFailed(f"Error communicating with {self._host}: {err}") from err

    async def async_send_control(self, attrs: dict):
        """Send a control command and refresh data."""
        success = await self.client.send_control(attrs)
        if success:
            await asyncio.sleep(0.5)
            await self.async_request_refresh()
        return success
