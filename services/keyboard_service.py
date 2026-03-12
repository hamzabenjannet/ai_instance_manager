from __future__ import annotations
import logging
logger = logging.getLogger(__name__)

def _pyautogui():
    try:
        import pyautogui
    except Exception as e:
        raise RuntimeError("pyautogui is not installed or not available on this host") from e
    return pyautogui

def type_text(text: str, interval_seconds: float = 0.05) -> None:
    logger.debug("type_text called with text=%r interval_seconds=%r", text, interval_seconds)
    pyautogui = _pyautogui()
    try:
        pyautogui.write(text, interval=interval_seconds)
    except Exception as e:
        logger.exception("failed to type text %r", text)
        raise RuntimeError(f"failed to type text {text}") from e   


def press_key(key: str) -> None:
    logger.debug("press_key called with key=%r", key)
    pyautogui = _pyautogui()
    try:
        pyautogui.press(key)
    except Exception as e:
        logger.exception("failed to press key %r", key)
        raise RuntimeError(f"failed to press key {key}") from e 
    logger.debug("key %r pressed successfully", key)