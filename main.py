from fastapi import FastAPI

from app.config import get_settings
from routes.health import router as health_router
from routes.keyboard import router as keyboard_router
from routes.mouse import router as mouse_router
from routes.screen import router as screen_router
from routes.vision import router as vision_router

app = FastAPI(title="AI Instance Manager", description="Control mouse and keyboard", version="0.1.0")
app.include_router(health_router)
app.include_router(mouse_router)
app.include_router(keyboard_router)
app.include_router(screen_router)
app.include_router(vision_router)

@app.get("/")
def read_root():
    return {"message": "AI Instance Manager API is running"}

if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(app, host=settings.app_host, port=settings.app_port)
