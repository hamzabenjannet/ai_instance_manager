import logging

from fastapi import APIRouter, HTTPException, Query

# from app.logging_service import event_logger
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
                
        raise HTTPException(status_code=501, detail=str(e)) from e

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
                
        raise HTTPException(status_code=501, detail=str(e)) from e
    except Exception as e:
        logger.exception("screen.screenshot unexpected error")
                
        raise HTTPException(status_code=500, detail="unexpected error") from e

    logger.debug(
        "screen.screenshot success encoding=%s image_name=%s base64_len=%d",
        "base64_png",
        image_name,
        len(encoded_base64_value),
    )
    logger.debug("screen.screenshot ok image_name=%s base64_len=%d", image_name, len(encoded_base64_value))
    return {"encoding": "base64_png", "encoded_base64": encoded_base64_value, "image_name": image_name}


# add route to get an image by name {"image_name": "screenshot_2026-03-13_15-43-45.png"} output image data data to be able to be used in an <image src="data:image/png;base64,{{encoded_base64}}">
@router.get("/image")
def get_image(image_name: str = Query(..., description="The name of the image to retrieve")) -> dict[str, str]:
    try:
        logger.debug("screen.image start image_name=%s", image_name)
        image_data = screen_service.get_image(image_name)
    except FileNotFoundError as e:
        logger.exception("screen.image error image_name=%s", image_name)
                
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.exception("screen.image unexpected error image_name=%s", image_name)
                
        raise HTTPException(status_code=500, detail="unexpected error") from e

    logger.debug("screen.image ok image_name=%s image_len=%d", image_name, len(image_data))
    return {"encoding": "base64_png", "encoded_base64": image_data, "image_name": image_name}


# add a route to retrieve the annotated image by name {"image_name": "annotated_screenshot_2026-03-13_16-01-17.png"} output image data data to be able to be used in an <image src="data:image/png;base64,{{encoded_base64}}">
@router.get("/annotated-image")
def get_annotated_image(image_name: str = Query(..., description="The name of the annotated image to retrieve")) -> dict[str, str]:
    try:
        logger.debug("screen.annotated_image start image_name=%s", image_name)
        image_data = screen_service.get_annotated_image(image_name)
    except FileNotFoundError as e:
        logger.exception("screen.annotated_image error image_name=%s", image_name)
                
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.exception("screen.annotated_image unexpected error image_name=%s", image_name)
                
        raise HTTPException(status_code=500, detail="unexpected error") from e

    logger.debug("screen.annotated_image ok image_name=%s image_len=%d", image_name, len(image_data))
    return {"encoding": "base64_png", "encoded_base64": image_data, "image_name": image_name}
