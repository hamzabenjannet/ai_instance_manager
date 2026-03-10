from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.logging_service import event_logger
from services import vision_service


router = APIRouter(prefix="/vision", tags=["vision"])


class VisionDetectRequest(BaseModel):
    image_name: str = Field(
        ...,
        description=(
            "Filename or path of the screenshot to analyse. "
            "Examples: 'screenshot_2026-03-10_14-44-52.png' "
            "or 'output/screenshots/screenshot_2026-03-10_14-44-52.png'"
        ),
        min_length=1,
    )
    use_yolo: bool = Field(default=True, description="Run YOLOv8 object detection")
    use_cv2_heuristic: bool = Field(
        default=True,
        description="Run OpenCV heuristic UI element detection (windows, toolbars, buttons, stripes)",
    )
    confidence_threshold: float = Field(
        default=0.25,
        ge=0.0,
        le=1.0,
        description="Minimum confidence score to include a detected box",
    )
    annotate: bool = Field(
        default=True,
        description="Save an annotated copy of the image to output/annotated/",
    )


@router.post("/detect")
def detect_elements(request: VisionDetectRequest) -> dict[str, Any]:
    """
    Detect UI elements in a screenshot.

    Runs YOLOv8 (object detection) and/or an OpenCV heuristic pass
    (window regions, title bars, toolbars) on the requested image file
    and returns a list of bounding boxes with coordinates and labels.

    The annotated image is saved to **output/annotated/** if `annotate=true`.
    """
    try:
        result = vision_service.detect_ui_elements(
            image_name=request.image_name,
            use_yolo=request.use_yolo,
            use_cv2_heuristic=request.use_cv2_heuristic,
            confidence_threshold=request.confidence_threshold,
            annotate=request.annotate,
        )
    except FileNotFoundError as e:
        event_logger.log("vision.detect", "error", {"error": str(e), "image_name": request.image_name})
        raise HTTPException(status_code=404, detail=str(e)) from e
    except RuntimeError as e:
        event_logger.log("vision.detect", "error", {"error": str(e), "image_name": request.image_name})
        raise HTTPException(status_code=501, detail=str(e)) from e

    event_logger.log(
        "vision.detect",
        "success",
        {
            "image_name": request.image_name,
            "count": result["count"],
            "annotated_path": result.get("annotated_path"),
            "errors": result.get("errors", []),
        },
    )
    return result