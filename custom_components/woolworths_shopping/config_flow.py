"""Config flow for Woolworths Shopping."""
import voluptuous as vol
from homeassistant import config_entries

DOMAIN = "woolworths_shopping"

class WoolworthsShoppingConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Woolworths Shopping."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            return self.async_create_entry(title="Woolworths Shopping", data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("username"): str,
                    vol.Required("password"): str,
                }
            ),
            errors=errors,
        )
