import logging

from fastapi import APIRouter, HTTPException, Query

from app.logging_service import event_logger
from services import screen_service


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/screen", tags=["screen"])


@router.get("/size")
def get_screen_size() -> dict[str, int]:
    try:
        logger.debug("screen.size start")
        size = screen_service.get_screen_size()
    except RuntimeError as e:
        logger.exception("screen.size error")
        event_logger.log("screen.size", "error", {"error": str(e)})
        raise HTTPException(status_code=501, detail=str(e)) from e

    event_logger.log("screen.size", "success", {"width": size.width, "height": size.height})
    logger.debug("screen.size ok width=%d height=%d", size.width, size.height)
    return {"width": size.width, "height": size.height}


@router.get("/screenshot")
def take_screenshot(encoded_base64: bool = Query(default=True)) -> dict[str, str]:
    try:
        logger.debug("screen.screenshot start encoded_base64=%s", encoded_base64)
        screenshot_base64 = screen_service.take_screenshot_base64()
        image_name = screenshot_base64["image_name"]
        encoded_base64_value = screenshot_base64["base64"] if encoded_base64 else "false"
    except RuntimeError as e:
        logger.exception("screen.screenshot error")
        event_logger.log("screen.screenshot", "error", {"error": str(e)})
        raise HTTPException(status_code=501, detail=str(e)) from e
    except Exception as e:
        logger.exception("screen.screenshot unexpected error")
        event_logger.log("screen.screenshot", "error", {"error": str(e)})
        raise HTTPException(status_code=500, detail="unexpected error") from e

    event_logger.log(
        "screen.screenshot",
        "success",
        {"encoding": "base64_png", "image_name": image_name, "base64_len": len(encoded_base64_value)},
    )
    logger.debug("screen.screenshot ok image_name=%s base64_len=%d", image_name, len(encoded_base64_value))
    return {"encoding": "base64_png", "encoded_base64": encoded_base64_value, "image_name": image_name}
