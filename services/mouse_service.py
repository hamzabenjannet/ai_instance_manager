from __future__ import annotations

from typing import Literal


def _pyautogui():
    try:
        import pyautogui
    except Exception as e:
        raise RuntimeError("pyautogui is not installed or not available on this host") from e
    return pyautogui


def get_position() -> tuple[int, int]:
    pyautogui = _pyautogui()
    point = pyautogui.position()
    return int(point.x), int(point.y)


def move_to(x: int, y: int) -> None:
    pyautogui = _pyautogui()
    pyautogui.moveTo(x, y)


def click(button: Literal["left", "right", "middle"] = "left") -> None:
    pyautogui = _pyautogui()
    pyautogui.click(button=button)
