from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from core.pipelines.face_swap import FaceSwapRequest, swap

router = APIRouter()

_uploads = Path("outputs") / "uploads"
_outputs = Path("outputs") / "face_swap"
_uploads.mkdir(parents=True, exist_ok=True)
_outputs.mkdir(parents=True, exist_ok=True)


class SwapResponse(BaseModel):
    job_id: str
    output_url: str
    faces_swapped: int


@router.post("/swap", response_model=SwapResponse)
async def face_swap_endpoint(
    source_image: UploadFile = File(..., description="Donor face image"),
    target_media: UploadFile = File(..., description="Target image or video"),
    blend_alpha: float = Form(-1.0),
    enhance: bool = Form(True),
):
    job_id = uuid.uuid4().hex

    src_path = _uploads / f"{job_id}_source{Path(source_image.filename).suffix}"
    tgt_path = _uploads / f"{job_id}_target{Path(target_media.filename).suffix}"
    src_path.write_bytes(await source_image.read())
    tgt_path.write_bytes(await target_media.read())

    out_ext = Path(target_media.filename).suffix or ".mp4"
    out_path = _outputs / f"{job_id}_swapped{out_ext}"

    try:
        result = swap(FaceSwapRequest(
            source_image=src_path,
            target_media=tgt_path,
            blend_alpha=blend_alpha,
            enhance=enhance,
            output_path=out_path,
        ))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    media_type = "video/mp4" if out_ext in {".mp4", ".avi", ".mov"} else "image/jpeg"
    return SwapResponse(
        job_id=job_id,
        output_url=f"/api/face-swap/result/{job_id}",
        faces_swapped=result.faces_swapped,
    )


@router.get("/result/{job_id}")
def get_result(job_id: str):
    for ext in [".mp4", ".avi", ".mov", ".jpg", ".png"]:
        path = _outputs / f"{job_id}_swapped{ext}"
        if path.exists():
            mt = "video/mp4" if ext in {".mp4", ".avi", ".mov"} else "image/jpeg"
            return FileResponse(str(path), media_type=mt)
    raise HTTPException(status_code=404, detail="Job not found")
