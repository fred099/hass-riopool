"""Config flow for Riopool Rio750 Pool Pump."""

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST

from .const import DOMAIN, LOGGER
from .gizwits_lan import GizwitsLanClient, discover_devices


class RiopoolConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Riopool."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            host = user_input[CONF_HOST]

            # Test connection
            client = GizwitsLanClient(host)
            try:
                status = await client.read_status()
                if status:
                    await self.async_set_unique_id(f"riopool_{host}")
                    self._abort_if_unique_id_configured()

                    return self.async_create_entry(
                        title=f"Riopool Rio750 ({host})",
                        data={CONF_HOST: host},
                    )
                else:
                    errors["base"] = "cannot_connect"
            except Exception:
                LOGGER.exception("Unexpected error during setup")
                errors["base"] = "unknown"
            finally:
                await client.disconnect()

        # Try auto-discovery
        suggested_host = ""
        try:
            devices = await discover_devices(timeout=3.0)
            if devices:
                suggested_host = devices[0]["host"]
        except Exception:
            pass

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST, default=suggested_host): str,
                }
            ),
            errors=errors,
        )
