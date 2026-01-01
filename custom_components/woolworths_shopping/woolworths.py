"""Service for interacting with Woolworths online."""
import asyncio
import logging
import datetime
import re
from playwright.async_api import async_playwright
from homeassistant.core import HomeAssistant
from homeassistant.components.persistent_notification import async_create
from urllib.parse import quote

_LOGGER = logging.getLogger(__name__)

class WoolworthsShoppingService:
    """Service to interact with Woolworths."""

    def __init__(self, hass: HomeAssistant, username, password):
        """Initialize the service."""
        self.hass = hass
        self.username = username
        self.password = password
        self.mfa_code = None
        self.mfa_event = asyncio.Event()

    async def get_shopping_list_items(self, list_name):
        """Get items from a Home Assistant shopping list."""
        try:
            # Note: The 'todo' domain and the service to get list items might differ.
            # This is a potential point of failure if the service call is incorrect.
            # Using hass.services.async_call to get the todo list items.
            # The service name is 'todo.get_items' and it requires the 'entity_id'.
            todo_items = await self.hass.services.async_call(
                'todo',
                'get_items',
                {'entity_id': f'todo.{list_name}'},
                blocking=True,
                return_response=True
            )
            return [item['summary'] for item in todo_items.get('items', [])]
        except Exception as e:
            _LOGGER.error(f"Error fetching shopping list: {e}")
            return []

    async def add_shopping_list_to_cart(self, shopping_list_name):
        """Add items from a shopping list to the Woolworths cart."""
        _LOGGER.info("Starting Woolworths shopping list to cart service")
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1024},
                ignore_https_errors=True
            )
            page = await context.new_page()
            page.set_default_navigation_timeout(300000)

            # Block ads and trackers
            ad_block_list = [
                "doubleclick.net",
                "googleadservices.com",
                "googlesyndication.com",
                "google-analytics.com",
                "ads.google.com",
            ]
            await page.route(re.compile(r"(\.|\/\/)(" + "|".join(ad_block_list) + ")"),
                             lambda route: route.abort())
            try:
                await page.goto("https://auth.woolworths.com.au/u/login")
                await page.fill("#username", self.username)
                await page.fill("#password", self.password)
                await page.click("input[type=submit]")
                await page.wait_for_load_state()

                if page.url.startswith("https://auth.woolworths.com.au/u/mfa-phone-challenge"):
                    _LOGGER.info("MFA required")
                    await page.click("button:has-text('Continue')")

                    # Create a persistent notification to ask for the MFA code
                    async_create(
                        self.hass,
                        "Please enter the 2FA code for Woolworths.",
                        title="Woolworths 2FA Required",
                        notification_id="woolworths_mfa",
                    )

                    try:
                        # Wait for the MFA code to be submitted
                        await asyncio.wait_for(self.mfa_event.wait(), timeout=300)
                        await page.fill("#code", self.mfa_code)
                        await page.click("button:has-text('Continue')")
                        await page.wait_for_load_state()
                        self.mfa_event.clear() # Reset the event
                    except asyncio.TimeoutError:
                        _LOGGER.error("Timed out waiting for MFA code.")
                        return


                _LOGGER.info("Login successful")

                shopping_list = await self.get_shopping_list_items(shopping_list_name)
                if not shopping_list:
                    _LOGGER.warning("Shopping list is empty or could not be fetched.")
                    return

                for item in shopping_list:
                    _LOGGER.info(f"Searching for {item}")
                    search_term = quote(item)
                    await page.goto(
                        f"https://www.woolworths.com.au/shop/search/products?searchTerm={search_term}"
                    )
                    await page.wait_for_load_state()

                    add_to_cart_button = page.locator("button:has-text('Add to cart')").first
                    if await add_to_cart_button.is_visible():
                        await add_to_cart_button.click()
                        _LOGGER.info(f"Added {item} to cart")
                        await asyncio.sleep(3)
                    else:
                        _LOGGER.warning(f"Could not find 'Add to cart' button for {item}")

                _LOGGER.info("Finished adding items to cart")
                await page.click("#header-view-cart-button")
                await asyncio.sleep(3)

                save_as_list_button = page.locator("button:has-text('Save as a list')")
                if await save_as_list_button.is_visible():
                    await save_as_list_button.click()
                    await page.wait_for_selector("#newListName")
                    list_name = f"Home assistant list ({datetime.datetime.now().strftime('%Y-%m-%d')})"
                    await page.fill("#newListName", list_name)
                    await page.click("button[type=submit]:has-text('Save')")
                    _LOGGER.info(f"Saved cart as list: {list_name}")
                else:
                    _LOGGER.warning("Could not find 'Save as a list' button")

            finally:
                await browser.close()

    def set_mfa_code(self, code):
        """Set the MFA code and notify the waiting service."""
        self.mfa_code = code
        self.mfa_event.set()
