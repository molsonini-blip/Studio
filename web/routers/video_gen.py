from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from core.pipelines.video_gen import VideoGenRequest, generate
from core.processing.video import pil_frames_to_video

router = APIRouter()

_outputs = Path("outputs") / "video_gen"
_outputs.mkdir(parents=True, exist_ok=True)


class GenerateRequest(BaseModel):
    prompt: str
    negative_prompt: str = ""
    pipeline: str = Field("animatediff", description="animatediff | stable_video_diffusion | cogvideox")
    num_frames: int = Field(16, ge=4, le=128)
    fps: int = Field(8, ge=1, le=60)
    width: int = Field(512, ge=64, le=1024)
    height: int = Field(512, ge=64, le=1024)
    guidance_scale: float = Field(7.5, ge=1.0, le=20.0)
    num_inference_steps: int = Field(25, ge=1, le=100)
    seed: int = -1


class GenerateResponse(BaseModel):
    job_id: str
    output_url: str
    frames: int
    fps: int
    pipeline_used: str


@router.post("/generate", response_model=GenerateResponse)
def generate_video(body: GenerateRequest):
    try:
        req = VideoGenRequest(**body.model_dump())
        result = generate(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    job_id = uuid.uuid4().hex
    out_path = _outputs / f"{job_id}.mp4"
    pil_frames_to_video(result.frames, out_path, fps=result.fps)

    return GenerateResponse(
        job_id=job_id,
        output_url=f"/api/video-gen/result/{job_id}",
        frames=len(result.frames),
        fps=result.fps,
        pipeline_used=result.pipeline_used,
    )


@router.get("/result/{job_id}")
def get_result(job_id: str):
    path = _outputs / f"{job_id}.mp4"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Job not found")
    return FileResponse(str(path), media_type="video/mp4")


@router.get("/pipelines")
def list_pipelines():
    return {"pipelines": ["animatediff", "stable_video_diffusion", "cogvideox"]}
