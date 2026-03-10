import unittest
from importlib.util import find_spec


class ScreenRoutesTest(unittest.TestCase):
    def test_screen_routes_registered(self) -> None:
        if find_spec("fastapi") is None:
            raise unittest.SkipTest("fastapi is not installed")

        from main import app

        paths = {route.path for route in app.router.routes}
        self.assertIn("/screen/size", paths)
        self.assertIn("/screen/screenshot", paths)
