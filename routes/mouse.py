import logging

from fastapi import APIRouter, HTTPException

# from app.logging_service import event_logger
from models.mouse_models import MouseClickRequest, MousePositionResponse, MoveMouseRequest
from services import mouse_service


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mouse", tags=["mouse"])


@router.get("/position", response_model=MousePositionResponse)
def get_mouse_position() -> MousePositionResponse:
    try:
        logger.debug("mouse.position start")
        x, y = mouse_service.get_position()
        logger.debug("mouse.position ok x=%d y=%d", x, y)
    except RuntimeError as e:
        logger.exception("mouse.position error")
        logger.debug("mouse.position error error=%s", str(e))
        raise HTTPException(status_code=501, detail=str(e)) from e

    logger.debug("mouse.position success x=%d y=%d", x, y)
    return MousePositionResponse(x=x, y=y)


@router.post("/move")
def move_mouse(request: MoveMouseRequest) -> dict[str, str]:
    try:
        logger.debug("mouse.move start x=%d y=%d", request.x, request.y)
        mouse_service.move_to(request.x, request.y)
    except RuntimeError as e:
        logger.exception("mouse.move error x=%d y=%d", request.x, request.y)
        logger.debug("mouse.move error x=%d y=%d error=%s", request.x, request.y, str(e))
        raise HTTPException(status_code=501, detail=str(e)) from e

    logger.debug("mouse.move success x=%d y=%d", request.x, request.y)
    logger.debug("mouse.move ok x=%d y=%d", request.x, request.y)
    return {"status": "ok"}


@router.post("/click")
def click_mouse(request: MouseClickRequest) -> dict[str, str]:
    try:
        logger.debug("mouse.click start button=%s", request.button)
        mouse_service.click(button=request.button)
    except RuntimeError as e:
        logger.exception("mouse.click error button=%s", request.button)
        logger.debug("mouse.click error button=%s error=%s", request.button, str(e))
        raise HTTPException(status_code=501, detail=str(e)) from e

    logger.debug("mouse.click success button=%s", request.button)
    logger.debug("mouse.click ok button=%s", request.button)
    return {"status": "ok"}
