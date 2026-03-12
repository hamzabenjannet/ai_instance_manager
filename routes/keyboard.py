import logging

from fastapi import APIRouter, HTTPException

from app.logging_service import event_logger
from models.keyboard_models import PressKeyRequest, TypeTextRequest
from services import keyboard_service


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/keyboard", tags=["keyboard"])


@router.post("/type")
def type_text(request: TypeTextRequest) -> dict[str, str]:
    try:
        logger.debug("keyboard.type start length=%d interval_seconds=%s", len(request.text), request.interval_seconds)
        keyboard_service.type_text(request.text, interval_seconds=request.interval_seconds)
    except RuntimeError as e:
        logger.exception("keyboard.type error")
        event_logger.log("keyboard.type", "error", {"error": str(e)})
        raise HTTPException(status_code=501, detail=str(e)) from e
    except Exception as e:
        logger.exception("keyboard.type unexpected error")
        event_logger.log("keyboard.type", "error", {"error": str(e)})
        raise HTTPException(status_code=500, detail="unexpected error") from e

    event_logger.log("keyboard.type", "success", {"length": len(request.text)})
    logger.debug("keyboard.type ok length=%d", len(request.text))
    return {"status": "ok"}


@router.post("/press")
def press_key(request: PressKeyRequest) -> dict[str, str]:
    try:
        logger.debug("keyboard.press start key=%s interval_seconds=%s", request.key, request.interval_seconds)
        keyboard_service.press_key(request.key, interval_seconds=request.interval_seconds)
    except RuntimeError as e:
        logger.exception("keyboard.press error key=%s", request.key)
        event_logger.log("keyboard.press", "error", {"error": str(e), "key": request.key})
        raise HTTPException(status_code=501, detail=str(e)) from e
    except Exception as e:
        logger.exception("keyboard.press unexpected error key=%s", request.key)
        event_logger.log("keyboard.press", "error", {"error": str(e), "key": request.key})
        raise HTTPException(status_code=500, detail="unexpected error") from e

    event_logger.log("keyboard.press", "success", {"key": request.key})
    logger.debug("keyboard.press ok key=%s", request.key)
    return {"status": "ok"}
