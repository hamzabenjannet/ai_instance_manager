from __future__ import annotations

import base64
from dataclasses import dataclass
from io import BytesIO


def _pyautogui():
    try:
        import pyautogui
    except Exception as e:
        raise RuntimeError("pyautogui is not installed or not available on this host") from e
    return pyautogui


@dataclass(frozen=True)
class ScreenSize:
    width: int
    height: int


def get_screen_size() -> ScreenSize:
    pyautogui = _pyautogui()
    size = pyautogui.size()
    return ScreenSize(width=int(size.width), height=int(size.height))


def take_screenshot_base64() -> str:
    pyautogui = _pyautogui()
    image = pyautogui.screenshot()
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")
