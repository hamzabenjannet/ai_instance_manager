from __future__ import annotations

import base64
from dataclasses import dataclass
from io import BytesIO
import os
from datetime import datetime


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
    try:
        images_output_absolute_dir_path = os.path.abspath("output/screenshots")
        os.makedirs(images_output_absolute_dir_path, exist_ok=True)
        pyautogui = _pyautogui()
        image = pyautogui.screenshot()
        
        # save to file
        date_and_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        image_name = f"screenshot_{date_and_time}.png"
        image_absolute_path = f"{images_output_absolute_dir_path}/{image_name}"
        image.save(image_absolute_path)
        
        # read back from file and encode
        with open(image_absolute_path, "rb") as f:
            return base64.b64encode(f.read()).decode("ascii")
    except Exception as e:
        return str(e)
