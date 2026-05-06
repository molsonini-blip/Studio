from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import yaml

from core.models.manager import manager
from core.pipelines.base import BasePipeline


def _cfg() -> dict:
    p = Path(__file__).resolve().parents[2] / "config" / "settings.yaml"
    with open(p) as f:
        return yaml.safe_load(f)["face_swap"]


@dataclass
class FaceSwapRequest:
    source_image: Path          # image containing the donor face
    target_media: Path          # image or video to receive the face
    blend_alpha: float = -1.0   # -1 → use config default
    enhance: bool = True        # run face enhancer post-swap
    output_path: Path | None = None


@dataclass
class FaceSwapResult:
    output_path: Path
    faces_swapped: int


class FaceSwapPipeline(BasePipeline):
    """InsightFace-based face swapper with optional GFPGAN enhancement."""

    name = "face_swap"

    def __init__(self) -> None:
        super().__init__()
        self._app: Any = None      # InsightFace FaceAnalysis
        self._swapper: Any = None  # onnxruntime swapper
        self._enhancer: Any = None # GFPGAN (optional)

    # ------------------------------------------------------------------
    def load(self) -> None:
        if self._loaded:
            return
        import insightface
        from insightface.app import FaceAnalysis

        cfg = _cfg()
        self._app = FaceAnalysis(name=cfg["detector_model"], providers=["CUDAExecutionProvider", "CPUExecutionProvider"])
        self._app.prepare(ctx_id=0 if manager.device.type == "cuda" else -1, det_size=(640, 640))

        swapper_path = manager.model_path("face_swap", cfg["swapper_model"])
        if not swapper_path.exists():
            raise FileNotFoundError(
                f"Swapper model not found: {swapper_path}\n"
                "Run scripts/download_models.py to download it."
            )
        self._swapper = insightface.model_zoo.get_model(str(swapper_path), providers=["CUDAExecutionProvider", "CPUExecutionProvider"])
        self._swapper.prepare(ctx_id=0 if manager.device.type == "cuda" else -1)

        if cfg.get("enhance_face"):
            self._load_enhancer(cfg)

        self._loaded = True

    def _load_enhancer(self, cfg: dict) -> None:
        try:
            from gfpgan import GFPGANer

            enhancer_path = manager.model_path("enhancers", cfg["enhancer_model"])
            if enhancer_path.exists():
                self._enhancer = GFPGANer(
                    model_path=str(enhancer_path),
                    upscale=1,
                    arch="clean",
                    channel_multiplier=2,
                )
        except ImportError:
            pass  # GFPGAN optional

    def unload(self) -> None:
        self._app = None
        self._swapper = None
        self._enhancer = None
        self._loaded = False

    # ------------------------------------------------------------------
    def run(self, req: FaceSwapRequest) -> FaceSwapResult:
        self.load()
        cfg = _cfg()
        alpha = req.blend_alpha if req.blend_alpha >= 0 else cfg["blend_alpha"]

        ext = req.target_media.suffix.lower()
        if ext in {".mp4", ".avi", ".mov", ".mkv"}:
            return self._swap_video(req, alpha)
        else:
            return self._swap_image(req, alpha)

    # ------------------------------------------------------------------
    def _get_source_face(self, source_path: Path):
        img = cv2.imread(str(source_path))
        faces = self._app.get(img)
        if not faces:
            raise ValueError(f"No face detected in source image: {source_path}")
        return sorted(faces, key=lambda f: f.bbox[2] - f.bbox[0], reverse=True)[0]

    def _swap_frame(self, frame: np.ndarray, source_face, alpha: float) -> tuple[np.ndarray, int]:
        target_faces = self._app.get(frame)
        count = 0
        for face in target_faces:
            swapped = self._swapper.get(frame, face, source_face, paste_back=True)
            if alpha < 1.0:
                frame = cv2.addWeighted(swapped, alpha, frame, 1 - alpha, 0)
            else:
                frame = swapped
            count += 1
        return frame, count

    def _enhance_frame(self, frame: np.ndarray) -> np.ndarray:
        if self._enhancer is None:
            return frame
        _, _, restored = self._enhancer.enhance(frame, has_aligned=False, only_center_face=False, paste_back=True)
        return restored if restored is not None else frame

    # ------------------------------------------------------------------
    def _swap_image(self, req: FaceSwapRequest, alpha: float) -> FaceSwapResult:
        source_face = self._get_source_face(req.source_image)
        frame = cv2.imread(str(req.target_media))
        frame, n = self._swap_frame(frame, source_face, alpha)
        if req.enhance:
            frame = self._enhance_frame(frame)

        out = req.output_path or req.target_media.with_stem(req.target_media.stem + "_swapped")
        cv2.imwrite(str(out), frame)
        return FaceSwapResult(output_path=out, faces_swapped=n)

    def _swap_video(self, req: FaceSwapRequest, alpha: float) -> FaceSwapResult:
        source_face = self._get_source_face(req.source_image)
        cap = cv2.VideoCapture(str(req.target_media))
        fps = cap.get(cv2.CAP_PROP_FPS)
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        out_path = req.output_path or req.target_media.with_stem(req.target_media.stem + "_swapped")
        writer = cv2.VideoWriter(str(out_path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))

        total_swaps = 0
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            frame, n = self._swap_frame(frame, source_face, alpha)
            if req.enhance:
                frame = self._enhance_frame(frame)
            writer.write(frame)
            total_swaps += n

        cap.release()
        writer.release()
        return FaceSwapResult(output_path=out_path, faces_swapped=total_swaps)


# Singleton instance
_pipeline: FaceSwapPipeline | None = None


def get_pipeline() -> FaceSwapPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = FaceSwapPipeline()
    return _pipeline


def swap(req: FaceSwapRequest) -> FaceSwapResult:
    return get_pipeline().run(req)
