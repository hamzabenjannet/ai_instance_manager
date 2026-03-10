from fastapi import APIRouter, HTTPException

from app.logging_service import event_logger
from services import screen_service


router = APIRouter(prefix="/screen", tags=["screen"])


@router.get("/size")
def get_screen_size() -> dict[str, int]:
    try:
        size = screen_service.get_screen_size()
    except RuntimeError as e:
        event_logger.log("screen.size", "error", {"error": str(e)})
        raise HTTPException(status_code=501, detail=str(e)) from e

    event_logger.log("screen.size", "success", {"width": size.width, "height": size.height})
    return {"width": size.width, "height": size.height}


@router.get("/screenshot")
def take_screenshot() -> dict[str, str]:
    try:
        screenshot_base64 = screen_service.take_screenshot_base64()
    except RuntimeError as e:
        event_logger.log("screen.screenshot", "error", {"error": str(e)})
        raise HTTPException(status_code=501, detail=str(e)) from e

    event_logger.log("screen.screenshot", "success", {"encoding": "base64_png"})
    return {"encoding": "base64_png", "data": screenshot_base64}
