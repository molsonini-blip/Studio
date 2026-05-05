from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from core.pipelines.talking_head import TalkingHeadRequest, animate

router = APIRouter()

_uploads = Path("outputs") / "uploads"
_outputs = Path("outputs") / "talking_head"
_uploads.mkdir(parents=True, exist_ok=True)
_outputs.mkdir(parents=True, exist_ok=True)


class AnimateResponse(BaseModel):
    job_id: str
    output_url: str
    duration_seconds: float


@router.post("/animate", response_model=AnimateResponse)
async def animate_endpoint(
    source_image: UploadFile = File(..., description="Portrait / anchor headshot"),
    audio: UploadFile = File(..., description="WAV or MP3 driving audio"),
    model: str = Form("sadtalker"),
    still_mode: bool = Form(True),
    preprocess: str = Form("crop"),
    enhance_face: bool = Form(True),
):
    job_id = uuid.uuid4().hex
    img_path = _uploads / f"{job_id}_portrait{Path(source_image.filename).suffix}"
    aud_path = _uploads / f"{job_id}_audio{Path(audio.filename).suffix}"
    img_path.write_bytes(await source_image.read())
    aud_path.write_bytes(await audio.read())

    out_path = _outputs / f"{job_id}.mp4"

    try:
        result = animate(TalkingHeadRequest(
            source_image=img_path,
            audio_path=aud_path,
            model=model,
            still_mode=still_mode,
            preprocess=preprocess,
            enhance_face=enhance_face,
            output_path=out_path,
        ))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return AnimateResponse(
        job_id=job_id,
        output_url=f"/api/talking-head/result/{job_id}",
        duration_seconds=result.duration_seconds,
    )


@router.get("/result/{job_id}")
def get_result(job_id: str):
    path = _outputs / f"{job_id}.mp4"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Job not found")
    return FileResponse(str(path), media_type="video/mp4")


@router.get("/models")
def list_models():
    return {"models": ["sadtalker", "wav2lip"]}
