from __future__ import annotations


def _pyautogui():
    try:
        import pyautogui
    except Exception as e:
        raise RuntimeError("pyautogui is not installed or not available on this host") from e
    return pyautogui


def type_text(text: str, interval_seconds: float = 0.05) -> None:
    pyautogui = _pyautogui()
    pyautogui.write(text, interval=interval_seconds)


def press_key(key: str) -> None:
    pyautogui = _pyautogui()
    pyautogui.press(key)
