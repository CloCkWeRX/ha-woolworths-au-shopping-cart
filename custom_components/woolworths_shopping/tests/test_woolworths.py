import unittest
from unittest.mock import MagicMock
from custom_components.woolworths_shopping.woolworths import WoolworthsShoppingService

class TestWoolworthsShoppingService(unittest.TestCase):
    def test_initialization(self):
        hass = MagicMock()
        username = "test_user"
        password = "test_password"
        service = WoolworthsShoppingService(hass, username, password)
        self.assertEqual(service.username, username)
        self.assertEqual(service.password, password)

if __name__ == '__main__':
    unittest.main()
