import unittest
from importlib.util import find_spec


class KeyboardRoutesTest(unittest.TestCase):
    def test_keyboard_routes_registered(self) -> None:
        if find_spec("fastapi") is None:
            raise unittest.SkipTest("fastapi is not installed")

        from main import app

        paths = {route.path for route in app.router.routes}
        self.assertIn("/keyboard/type", paths)
        self.assertIn("/keyboard/press", paths)
