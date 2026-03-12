import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.logging_service import event_logger
from services import vision_service


logger = logging.getLogger(__name__)

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
        description="Run OpenCV heuristic UI element detection (windows, toolbars, stripes)",
    )
    use_florence: bool = Field(
        default=False,
        description=(
            "Run Florence-2 for natural-language element description. "
            "WARNING: slow on CPU (~0.5-2s per box). Use async/queue for production."
        ),
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
    use_gpu: bool = Field(
        default=False,
        description=(
            "Use GPU acceleration for YOLO inference. "
            "Automatically selects CUDA (Nvidia) or MPS (Apple Silicon). "
            "Falls back to CPU silently if no GPU is available. "
            "Keep false until GPU passthrough is configured in Docker."
        ),
    )


@router.post("/detect")
def detect_elements(request: VisionDetectRequest) -> dict[str, Any]:
    """
    Detect UI elements in a screenshot.

    Runs YOLOv8 and/or OpenCV heuristic detection on the requested image file
    and returns bounding boxes with coordinates, labels, and center points.

    - **use_gpu**: keep false for CPU-only containers; set true when CUDA/MPS is available.
    - Annotated image saved to output/annotated/ when annotate=true.
    """
    try:
        logger.debug(
            "vision.detect start image_name=%s use_yolo=%s use_cv2_heuristic=%s use_florence=%s confidence_threshold=%s annotate=%s use_gpu=%s",
            request.image_name,
            request.use_yolo,
            request.use_cv2_heuristic,
            request.use_florence,
            request.confidence_threshold,
            request.annotate,
            request.use_gpu,
        )
        result = vision_service.detect_ui_elements(
            image_name=request.image_name,
            use_yolo=request.use_yolo,
            use_cv2_heuristic=request.use_cv2_heuristic,
            use_florence=request.use_florence,     # Phase 2 — opt-in, slow on CPU
            confidence_threshold=request.confidence_threshold,
            annotate=request.annotate,
            use_gpu=request.use_gpu,
        )
    except FileNotFoundError as e:
        logger.exception("vision.detect file not found image_name=%s", request.image_name)
        event_logger.log("vision.detect", "error", {"error": str(e), "image_name": request.image_name})
        raise HTTPException(status_code=404, detail=str(e)) from e
    except RuntimeError as e:
        logger.exception("vision.detect runtime error image_name=%s", request.image_name)
        event_logger.log("vision.detect", "error", {"error": str(e), "image_name": request.image_name})
        raise HTTPException(status_code=501, detail=str(e)) from e
    except Exception as e:
        logger.exception("vision.detect unexpected error image_name=%s", request.image_name)
        event_logger.log("vision.detect", "error", {"error": str(e), "image_name": request.image_name})
        raise HTTPException(status_code=500, detail="unexpected error") from e

    event_logger.log(
        "vision.detect",
        "success",
        {
            "image_name": request.image_name,
            "use_yolo": request.use_yolo,
            "use_cv2_heuristic": request.use_cv2_heuristic,
            "confidence_threshold": request.confidence_threshold,
            "count": result["count"],
            "use_gpu": request.use_gpu,
            "annotated_path": result.get("annotated_path"),
            "errors": result.get("errors", []),
        },
    )
    logger.debug(
        "vision.detect ok image_name=%s count=%s annotated_path=%s errors_count=%d",
        request.image_name,
        result.get("count"),
        result.get("annotated_path"),
        len(result.get("errors", [])),
    )
    return result
