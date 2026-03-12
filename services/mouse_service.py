from __future__ import annotations

import logging
from typing import Literal


logger = logging.getLogger(__name__)


def _pyautogui():
    try:
        import pyautogui
    except Exception as e:
        logger.exception("pyautogui import failed")
        raise RuntimeError("pyautogui is not installed or not available on this host") from e
    return pyautogui


def get_position() -> tuple[int, int]:
    pyautogui = _pyautogui()
    try:
        point = pyautogui.position()
        x, y = int(point.x), int(point.y)
        logger.debug("mouse position x=%d y=%d", x, y)
        return x, y
    except Exception as e:
        logger.exception("failed to get mouse position")
        raise RuntimeError("failed to get mouse position") from e


def move_to(x: int, y: int) -> None:
    pyautogui = _pyautogui()
    try:
        pyautogui.moveTo(x, y)
        logger.debug("mouse moved to x=%d y=%d", x, y)
    except Exception as e:
        logger.exception("failed to move mouse x=%d y=%d", x, y)
        raise RuntimeError(f"failed to move mouse to x={x} y={y}") from e


def click(button: Literal["left", "right", "middle", "doubleLeft"] = "left") -> None:
    pyautogui = _pyautogui()
    try:
        if button == "doubleLeft":
            pyautogui.doubleClick(button="left")
        else:
            pyautogui.click(button=button)
    except Exception as e:
        logger.exception("failed to click button=%s", button)
        raise RuntimeError(f"failed to click button={button}") from e
    logger.debug("mouse click ok button=%s", button)
