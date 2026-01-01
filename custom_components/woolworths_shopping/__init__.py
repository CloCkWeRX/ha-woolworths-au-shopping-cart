"""The Woolworths Shopping integration."""
import logging
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from .woolworths import WoolworthsShoppingService

DOMAIN = "woolworths_shopping"
_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Woolworths Shopping component."""
    hass.data[DOMAIN] = {}
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Woolworths Shopping from a config entry."""
    service = WoolworthsShoppingService(
        hass,
        entry.data["username"],
        entry.data["password"],
    )
    hass.data[DOMAIN][entry.entry_id] = service

    async def add_shopping_list_to_cart(call):
        """Handle the service call."""
        shopping_list_name = call.data.get("shopping_list_name", "shopping")
        await service.add_shopping_list_to_cart(shopping_list_name)

    async def submit_mfa_code(call):
        """Handle the service call to submit MFA code."""
        code = call.data.get("code")
        service.set_mfa_code(code)

    hass.services.async_register(
        DOMAIN,
        "add_shopping_list_to_cart",
        add_shopping_list_to_cart,
    )

    hass.services.async_register(
        DOMAIN,
        "submit_mfa_code",
        submit_mfa_code,
    )

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    hass.data[DOMAIN].pop(entry.entry_id)
    return True
