from fastapi import APIRouter, HTTPException

from app.logging_service import event_logger
from models.keyboard_models import PressKeyRequest, TypeTextRequest
from services import keyboard_service


router = APIRouter(prefix="/keyboard", tags=["keyboard"])


@router.post("/type")
def type_text(request: TypeTextRequest) -> dict[str, str]:
    try:
        keyboard_service.type_text(request.text, interval_seconds=request.interval_seconds)
    except RuntimeError as e:
        event_logger.log("keyboard.type", "error", {"error": str(e)})
        raise HTTPException(status_code=501, detail=str(e)) from e

    event_logger.log("keyboard.type", "success", {"length": len(request.text)})
    return {"status": "ok"}


@router.post("/press")
def press_key(request: PressKeyRequest) -> dict[str, str]:
    try:
        keyboard_service.press_key(request.key)
    except RuntimeError as e:
        event_logger.log("keyboard.press", "error", {"error": str(e), "key": request.key})
        raise HTTPException(status_code=501, detail=str(e)) from e

    event_logger.log("keyboard.press", "success", {"key": request.key})
    return {"status": "ok"}
