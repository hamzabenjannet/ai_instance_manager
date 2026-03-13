from __future__ import annotations

import base64
from dataclasses import dataclass
import logging
import os
from datetime import datetime


logger = logging.getLogger(__name__)


def _pyautogui():
    try:
        import pyautogui
    except Exception as e:
        logger.exception("pyautogui import failed")
        raise RuntimeError("pyautogui is not installed or not available on this host") from e
    return pyautogui


@dataclass(frozen=True)
class ScreenSize:
    width: int
    height: int


def get_screen_size() -> ScreenSize:
    pyautogui = _pyautogui()
    try:
        size = pyautogui.size()
        result = ScreenSize(width=int(size.width), height=int(size.height))
        logger.debug("screen size width=%d height=%d", result.width, result.height)
        return result
    except Exception as e:
        logger.exception("failed to get screen size")
        raise RuntimeError("failed to get screen size") from e


def take_screenshot_base64() -> dict[str, str]:
    try:
        images_output_absolute_dir_path = os.path.abspath("output/screenshots")
        os.makedirs(images_output_absolute_dir_path, exist_ok=True)
        pyautogui = _pyautogui()
        logger.debug("taking screenshot output_dir=%s", images_output_absolute_dir_path)
        image = pyautogui.screenshot()
        
        date_and_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        image_name = f"screenshot_{date_and_time}.png"
        image_absolute_path = f"{images_output_absolute_dir_path}/{image_name}"
        image.save(image_absolute_path)
        
        with open(image_absolute_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("ascii")
        logger.debug("screenshot saved image_name=%s bytes_base64=%d", image_name, len(encoded))
        return {"base64": encoded, "image_name": image_name}
    except Exception as e:
        logger.exception("failed to take screenshot")
        raise RuntimeError("failed to take screenshot") from e


def get_image(image_name: str) -> str:
    images_output_absolute_dir_path = os.path.abspath("output/screenshots")
    safe_name = os.path.basename(image_name)
    if safe_name != image_name or not safe_name:
        raise FileNotFoundError("invalid image_name")

    image_absolute_path = os.path.join(images_output_absolute_dir_path, safe_name)
    if not os.path.isfile(image_absolute_path):
        raise FileNotFoundError(f"image not found: {safe_name}")

    try:
        with open(image_absolute_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("ascii")
        logger.debug("screen.get_image ok image_name=%s base64_len=%d", safe_name, len(encoded))
        return encoded
    except Exception as e:
        logger.exception("screen.get_image failed image_name=%s", safe_name)
        raise RuntimeError("failed to read image") from e


def get_annotated_image(image_name: str) -> str:
    images_output_absolute_dir_path = os.path.abspath("output/annotated")
    safe_name = os.path.basename(image_name)
    if safe_name != image_name or not safe_name:
        raise FileNotFoundError("invalid image_name")

    image_absolute_path = os.path.join(images_output_absolute_dir_path, safe_name)
    if not os.path.isfile(image_absolute_path):
        raise FileNotFoundError(f"image not found: {safe_name}")

    try:
        with open(image_absolute_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("ascii")
        logger.debug("screen.get_annotated_image ok image_name=%s base64_len=%d", safe_name, len(encoded))
        return encoded
    except Exception as e:
        logger.exception("screen.get_annotated_image failed image_name=%s", safe_name)
        raise RuntimeError("failed to read image") from e
