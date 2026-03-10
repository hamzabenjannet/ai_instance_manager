import unittest
from importlib.util import find_spec


class MouseRoutesTest(unittest.TestCase):
    def test_mouse_routes_registered(self) -> None:
        if find_spec("fastapi") is None:
            raise unittest.SkipTest("fastapi is not installed")

        from main import app

        paths = {route.path for route in app.router.routes}
        self.assertIn("/mouse/position", paths)
        self.assertIn("/mouse/move", paths)
        self.assertIn("/mouse/click", paths)
