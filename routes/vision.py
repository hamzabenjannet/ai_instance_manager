from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.logging_service import event_logger
from services import vision_service


router = APIRouter(prefix="/vision", tags=["vision"])


class VisionDetectRequest(BaseModel):
    image_base64: str | None = None


@router.post("/detect")
def detect_elements(request: VisionDetectRequest) -> dict[str, Any]:
    try:
        boxes = vision_service.detect_ui_elements(request.image_base64)
    except RuntimeError as e:
        event_logger.log("vision.detect", "error", {"error": str(e)})
        raise HTTPException(status_code=501, detail=str(e)) from e

    payload = [
        {
            "x": box.x,
            "y": box.y,
            "width": box.width,
            "height": box.height,
            "label": box.label,
            "score": box.score,
        }
        for box in boxes
    ]
    event_logger.log("vision.detect", "success", {"count": len(payload)})
    return {"count": len(payload), "boxes": payload}
