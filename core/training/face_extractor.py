from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np


def extract_anchor_frames(
    video_path: Path,
    output_dir: Path,
    sample_every_n_frames: int = 30,   # ~1 frame/sec at 30fps
    min_face_size: int = 80,           # pixels — skip tiny/distant faces
    max_frames: int = 500,
) -> list[Path]:
    """Extract clean single-face frames from an anchor video.

    Filters to frames where exactly one face is present and large enough,
    ensuring we get clean anchor head-shots for training.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Use OpenCV's fast Haar cascade for initial face detection
    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    detector = cv2.CascadeClassifier(cascade_path)

    cap = cv2.VideoCapture(str(video_path))
    frame_idx = 0
    saved: list[Path] = []

    while len(saved) < max_frames:
        ok, frame = cap.read()
        if not ok:
            break
        frame_idx += 1

        if frame_idx % sample_every_n_frames != 0:
            continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = detector.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(min_face_size, min_face_size)
        )

        # Keep only frames with exactly one face
        if len(faces) != 1:
            continue

        out_path = output_dir / f"frame_{frame_idx:06d}.jpg"
        cv2.imwrite(str(out_path), frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
        saved.append(out_path)

    cap.release()
    return saved


def extract_all_anchors(
    clips_manifest: Path,
    frames_output_dir: Path,
    sample_every_n_frames: int = 30,
    max_frames_per_clip: int = 200,
) -> dict[str, list[str]]:
    """Extract anchor frames from all clips listed in a manifest."""
    frames_output_dir = Path(frames_output_dir)
    with open(clips_manifest) as f:
        manifest = json.load(f)

    results: dict[str, list[str]] = {}
    for item in manifest:
        item_id = item["id"]
        video = Path(item["video"])
        if not video.exists():
            continue

        out_dir = frames_output_dir / item_id
        print(f"  extracting frames: {item_id}")
        frames = extract_anchor_frames(
            video, out_dir,
            sample_every_n_frames=sample_every_n_frames,
            max_frames=max_frames_per_clip,
        )
        results[item_id] = [str(f) for f in frames]
        print(f"    saved {len(frames)} frames")

    summary_path = frames_output_dir / "frames_index.json"
    with open(summary_path, "w") as f:
        json.dump(results, f, indent=2)

    total = sum(len(v) for v in results.values())
    print(f"Total anchor frames: {total} → {frames_output_dir}")
    return results
