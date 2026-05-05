from __future__ import annotations

from pathlib import Path
from typing import Iterator

import cv2
import numpy as np
from PIL import Image


# ── Frame I/O ─────────────────────────────────────────────────────────────────

def frames_from_video(path: Path) -> Iterator[np.ndarray]:
    """Yield BGR frames from a video file."""
    cap = cv2.VideoCapture(str(path))
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            yield frame
    finally:
        cap.release()


def frames_to_video(
    frames: list[np.ndarray] | list[Image.Image],
    output_path: Path,
    fps: float = 24.0,
    codec: str = "mp4v",
) -> Path:
    """Write a list of frames (numpy BGR or PIL RGB) to an mp4."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    first = frames[0]
    if isinstance(first, Image.Image):
        frames = [np.array(f.convert("RGB"))[:, :, ::-1] for f in frames]
        first = frames[0]

    h, w = first.shape[:2]
    writer = cv2.VideoWriter(str(output_path), cv2.VideoWriter_fourcc(*codec), fps, (w, h))
    for f in frames:
        writer.write(f)
    writer.release()
    return output_path


def pil_frames_to_video(frames: list[Image.Image], output_path: Path, fps: float = 8.0) -> Path:
    return frames_to_video(frames, output_path, fps=fps)


# ── Metadata ──────────────────────────────────────────────────────────────────

def video_info(path: Path) -> dict:
    cap = cv2.VideoCapture(str(path))
    info = {
        "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        "fps": cap.get(cv2.CAP_PROP_FPS),
        "frame_count": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
        "duration_seconds": 0.0,
    }
    if info["fps"] > 0:
        info["duration_seconds"] = info["frame_count"] / info["fps"]
    cap.release()
    return info


# ── Compositing ───────────────────────────────────────────────────────────────

def overlay_image(
    background: np.ndarray,
    overlay: np.ndarray,
    x: int,
    y: int,
    alpha: float = 1.0,
) -> np.ndarray:
    """Paste overlay onto background at (x, y) with optional alpha blend."""
    bg = background.copy()
    oh, ow = overlay.shape[:2]
    x2, y2 = min(x + ow, bg.shape[1]), min(y + oh, bg.shape[0])
    roi = bg[y:y2, x:x2]
    src = overlay[: y2 - y, : x2 - x]

    if overlay.shape[2] == 4:
        mask = src[:, :, 3:4] / 255.0 * alpha
        roi[:] = (src[:, :, :3] * mask + roi * (1 - mask)).astype(np.uint8)
    else:
        roi[:] = cv2.addWeighted(src, alpha, roi, 1 - alpha, 0)

    bg[y:y2, x:x2] = roi
    return bg


def add_lower_third(
    frame: np.ndarray,
    name: str,
    title: str,
    font_scale: float = 0.8,
    color: tuple[int, int, int] = (255, 255, 255),
    bg_color: tuple[int, int, int] = (20, 20, 20),
) -> np.ndarray:
    """Burn a news-anchor lower-third graphic onto a frame."""
    h, w = frame.shape[:2]
    out = frame.copy()

    bar_h = int(h * 0.12)
    bar_y = h - bar_h - int(h * 0.04)
    bar_x = int(w * 0.04)
    bar_w = int(w * 0.55)

    overlay = out.copy()
    cv2.rectangle(overlay, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), bg_color, -1)
    out = cv2.addWeighted(overlay, 0.75, out, 0.25, 0)

    font = cv2.FONT_HERSHEY_DUPLEX
    cv2.putText(out, name, (bar_x + 12, bar_y + int(bar_h * 0.48)), font, font_scale * 1.1, color, 2)
    cv2.putText(out, title, (bar_x + 12, bar_y + int(bar_h * 0.82)), font, font_scale * 0.75, (200, 200, 200), 1)
    return out


# ── Thumbnail ─────────────────────────────────────────────────────────────────

def extract_thumbnail(path: Path, timestamp_sec: float = 0.0) -> Image.Image:
    cap = cv2.VideoCapture(str(path))
    cap.set(cv2.CAP_PROP_POS_MSEC, timestamp_sec * 1000)
    ok, frame = cap.read()
    cap.release()
    if not ok:
        raise RuntimeError(f"Could not read frame at {timestamp_sec}s from {path}")
    return Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
