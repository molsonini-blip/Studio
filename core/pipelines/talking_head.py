from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import cv2
import numpy as np
import yaml

from core.models.manager import manager
from core.pipelines.base import BasePipeline


def _cfg() -> dict:
    p = Path(__file__).resolve().parents[3] / "config" / "settings.yaml"
    with open(p) as f:
        return yaml.safe_load(f)["talking_head"]


@dataclass
class TalkingHeadRequest:
    source_image: Path              # portrait / anchor headshot
    audio_path: Path                # WAV or MP3 driving audio
    model: str = "sadtalker"        # sadtalker | wav2lip
    still_mode: bool = True         # True = minimal head motion (anchor look)
    preprocess: str = "crop"        # crop | resize | full
    enhance_face: bool = True
    output_path: Path | None = None


@dataclass
class TalkingHeadResult:
    output_path: Path
    duration_seconds: float


# ──────────────────────────────────────────────────────────────────────────────
# SadTalker
# ──────────────────────────────────────────────────────────────────────────────

class SadTalkerPipeline(BasePipeline):
    """Audio-driven portrait animation via SadTalker.

    SadTalker is cloned into models/sadtalker/; this pipeline calls its
    inference script as a subprocess so we don't need to maintain a fork.
    """

    name = "sadtalker"

    def load(self) -> None:
        if self._loaded:
            return
        cfg = _cfg()["models"]["sadtalker"]
        checkpoint_dir = manager.model_path("sadtalker")
        if not checkpoint_dir.exists():
            raise FileNotFoundError(
                f"SadTalker checkpoints not found at {checkpoint_dir}.\n"
                "Run scripts/download_models.py to download them."
            )
        self._checkpoint_dir = checkpoint_dir
        self._loaded = True

    def unload(self) -> None:
        self._loaded = False

    def run(self, req: TalkingHeadRequest) -> TalkingHeadResult:
        self.load()
        out_dir = req.output_path.parent if req.output_path else manager.model_path().parent / "outputs" / "talking_head"
        out_dir.mkdir(parents=True, exist_ok=True)

        sadtalker_script = self._checkpoint_dir / "inference.py"
        cmd = [
            sys.executable,
            str(sadtalker_script),
            "--driven_audio", str(req.audio_path),
            "--source_image", str(req.source_image),
            "--checkpoint_dir", str(self._checkpoint_dir),
            "--result_dir", str(out_dir),
            "--preprocess", req.preprocess,
        ]
        if req.still_mode:
            cmd.append("--still")
        if req.enhance_face:
            cmd += ["--enhancer", "gfpgan"]

        subprocess.run(cmd, check=True)

        # SadTalker names output after the source image stem
        stem = req.source_image.stem
        candidates = sorted(out_dir.glob(f"{stem}*.mp4"))
        if not candidates:
            raise RuntimeError("SadTalker produced no output video.")
        result_path = candidates[-1]

        if req.output_path and req.output_path != result_path:
            result_path.rename(req.output_path)
            result_path = req.output_path

        duration = _video_duration(result_path)
        return TalkingHeadResult(output_path=result_path, duration_seconds=duration)


# ──────────────────────────────────────────────────────────────────────────────
# Wav2Lip
# ──────────────────────────────────────────────────────────────────────────────

class Wav2LipPipeline(BasePipeline):
    """Lip-sync driven by Wav2Lip GAN model.

    Suitable for cases where the source is a video (e.g., existing anchor footage)
    rather than a still image.
    """

    name = "wav2lip"

    def load(self) -> None:
        if self._loaded:
            return
        cfg = _cfg()["models"]["wav2lip"]
        ckpt = manager.model_path(*Path(cfg["checkpoint"]).parts[-2:])
        if not ckpt.exists():
            raise FileNotFoundError(
                f"Wav2Lip checkpoint not found at {ckpt}.\n"
                "Run scripts/download_models.py to download it."
            )
        self._ckpt = ckpt
        self._loaded = True

    def unload(self) -> None:
        self._loaded = False

    def run(self, req: TalkingHeadRequest) -> TalkingHeadResult:
        self.load()
        wav2lip_dir = manager.model_path("wav2lip")
        inference_script = wav2lip_dir / "inference.py"
        out_path = req.output_path or (
            Path("outputs") / "talking_head" / (req.source_image.stem + "_wav2lip.mp4")
        )
        out_path.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            sys.executable,
            str(inference_script),
            "--checkpoint_path", str(self._ckpt),
            "--face", str(req.source_image),
            "--audio", str(req.audio_path),
            "--outfile", str(out_path),
        ]
        subprocess.run(cmd, check=True)

        duration = _video_duration(out_path)
        return TalkingHeadResult(output_path=out_path, duration_seconds=duration)


# ──────────────────────────────────────────────────────────────────────────────
# Utility
# ──────────────────────────────────────────────────────────────────────────────

def _video_duration(path: Path) -> float:
    cap = cv2.VideoCapture(str(path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    n = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    cap.release()
    return n / fps


_PIPELINES: dict[str, type[BasePipeline]] = {
    "sadtalker": SadTalkerPipeline,
    "wav2lip": Wav2LipPipeline,
}
_instances: dict[str, BasePipeline] = {}


def get_pipeline(name: str) -> BasePipeline:
    if name not in _instances:
        cls = _PIPELINES.get(name)
        if cls is None:
            raise ValueError(f"Unknown talking-head model: {name!r}")
        _instances[name] = cls()
    return _instances[name]


def animate(req: TalkingHeadRequest) -> TalkingHeadResult:
    return get_pipeline(req.model).run(req)
