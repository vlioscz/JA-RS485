import voluptuous as vol
from homeassistant import config_entries
from .const import DOMAIN, CONF_PORT, CONF_BAUDRATE

DEFAULT_BAUDRATE = 9600

class JablotronAsciiConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow pro Jablotron RS485 ASCII."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            return self.async_create_entry(
                title=f"Jablotron ({user_input[CONF_PORT]})",
                data=user_input
            )

        schema = vol.Schema({
            vol.Required(CONF_PORT): str,
            vol.Optional(CONF_BAUDRATE, default=DEFAULT_BAUDRATE): int,
        })

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors
        )
