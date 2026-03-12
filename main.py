import logging
import os
import sys

from fastapi import FastAPI

from app.config import get_settings
from routes.health import router as health_router
from routes.keyboard import router as keyboard_router
from routes.mouse import router as mouse_router
from routes.screen import router as screen_router
from routes.ssh import router as ssh_router
from routes.vision import router as vision_router


def _configure_logging() -> None:
    level_name = os.getenv("APP_LOG_LEVEL") or os.getenv("LOG_LEVEL") or "DEBUG"
    level = getattr(logging, level_name.upper(), logging.DEBUG)

    root = logging.getLogger()
    if not root.handlers:
        logging.basicConfig(
            level=level,
            stream=sys.stdout,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )
    root.setLevel(level)
    for namespace in ("routes", "services", "app", "models", "utils"):
        logging.getLogger(namespace).setLevel(level)


_configure_logging()

app = FastAPI(title="AI Instance Manager", description="Control mouse and keyboard", version="0.1.0")
app.include_router(health_router)
app.include_router(mouse_router)
app.include_router(keyboard_router)
app.include_router(screen_router)
app.include_router(ssh_router)
app.include_router(vision_router)

try:
    from mcp_server.server import create_sse_app

    app.mount("/mcp", create_sse_app())
except Exception:
    logging.getLogger(__name__).exception("failed to mount mcp sse app")

@app.get("/")
def read_root():
    return {"message": "AI Instance Manager API is running"}

if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(app, host=settings.app_host, port=settings.app_port)
