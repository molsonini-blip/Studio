from __future__ import annotations

from pathlib import Path

import yaml
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from web.routers import face_swap, talking_head, video_gen

_cfg_path = Path(__file__).resolve().parents[1] / "config" / "settings.yaml"
with open(_cfg_path) as _f:
    _cfg = yaml.safe_load(_f)

app = FastAPI(
    title="Studio API",
    description="AI Video Imaging — local inference server",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cfg["web"]["cors_origins"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(video_gen.router, prefix="/api/video-gen", tags=["Video Generation"])
app.include_router(face_swap.router, prefix="/api/face-swap", tags=["Face Swap"])
app.include_router(talking_head.router, prefix="/api/talking-head", tags=["Talking Head"])

_static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")


@app.get("/", include_in_schema=False)
def root():
    return FileResponse(str(_static_dir / "index.html"))


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "web.main:app",
        host=_cfg["web"]["host"],
        port=_cfg["web"]["port"],
        reload=True,
    )
