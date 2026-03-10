from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

app = FastAPI(title="AI Instance Manager", description="Control mouse and keyboard", version="0.1.0")

@app.get("/")
def read_root():
    return {"message": "AI Instance Manager API is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=42014)