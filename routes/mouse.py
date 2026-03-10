from fastapi import APIRouter, HTTPException

from app.logging_service import event_logger
from models.mouse_models import MouseClickRequest, MousePositionResponse, MoveMouseRequest
from services import mouse_service


router = APIRouter(prefix="/mouse", tags=["mouse"])


@router.get("/position", response_model=MousePositionResponse)
def get_mouse_position() -> MousePositionResponse:
    try:
        x, y = mouse_service.get_position()
    except RuntimeError as e:
        event_logger.log("mouse.position", "error", {"error": str(e)})
        raise HTTPException(status_code=501, detail=str(e)) from e

    event_logger.log("mouse.position", "success", {"x": x, "y": y})
    return MousePositionResponse(x=x, y=y)


@router.post("/move")
def move_mouse(request: MoveMouseRequest) -> dict[str, str]:
    try:
        mouse_service.move_to(request.x, request.y)
    except RuntimeError as e:
        event_logger.log("mouse.move", "error", {"error": str(e), "x": request.x, "y": request.y})
        raise HTTPException(status_code=501, detail=str(e)) from e

    event_logger.log("mouse.move", "success", {"x": request.x, "y": request.y})
    return {"status": "ok"}


@router.post("/click")
def click_mouse(request: MouseClickRequest) -> dict[str, str]:
    try:
        mouse_service.click(button=request.button)
    except RuntimeError as e:
        event_logger.log("mouse.click", "error", {"error": str(e), "button": request.button})
        raise HTTPException(status_code=501, detail=str(e)) from e

    event_logger.log("mouse.click", "success", {"button": request.button})
    return {"status": "ok"}
