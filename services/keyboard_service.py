from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def _pyautogui():
    try:
        import pyautogui
    except Exception as e:
        logger.exception("pyautogui import failed")
        raise RuntimeError("pyautogui is not installed or not available on this host") from e
    return pyautogui


def type_text(text: str, interval_seconds: float = 0.05) -> None:
    logger.debug("type_text start length=%d interval_seconds=%s", len(text), interval_seconds)
    pyautogui = _pyautogui()
    try:
        pyautogui.write(text, interval=interval_seconds)
    except Exception as e:
        logger.exception("type_text error length=%d", len(text))
        raise RuntimeError("failed to type text") from e
    logger.debug("typed text successfully length=%d", len(text))


def press_key(key: str, interval_seconds: float = 0.05) -> None:
    logger.debug("press_key called with key=%r interval_seconds=%r", key, interval_seconds)
    pyautogui = _pyautogui()
    try:
        pyautogui.press(key, interval=interval_seconds)
    except Exception as e:
        logger.exception("failed to press key %r", key)
        raise RuntimeError(f"failed to press key {key}") from e
    logger.debug("key %r pressed successfully", key)
