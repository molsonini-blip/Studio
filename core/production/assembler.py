"""
Assembles per-anchor MP4 segments into a final broadcast video.
Each segment: anchor TTS video → lower-third overlay → title card.
Final output: concatenated broadcast with optional intro/outro.
"""
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path


STUDIO_DIR = Path(__file__).resolve().parents[2]
FONTS_DIR = STUDIO_DIR / "data" / "fonts"
ASSETS_DIR = STUDIO_DIR / "data" / "assets"


def _find_font() -> str:
    candidates = [
        FONTS_DIR / "DejaVuSans-Bold.ttf",
        Path("C:/Windows/Fonts/arialbd.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        Path("/System/Library/Fonts/Helvetica.ttc"),
    ]
    for p in candidates:
        if p.exists():
            return str(p).replace("\\", "/")
    return "sans-serif"


def add_lower_third(
    input_mp4: Path,
    output_mp4: Path,
    anchor_name: str,
    headline: str,
    duration: float | None = None,
) -> None:
    """Burn a lower-third graphic onto a video segment."""
    font = _find_font()
    safe_name = anchor_name.replace("'", "\\'")
    safe_headline = headline[:60].replace("'", "\\'").replace(":", "\\:")

    # two-line lower third: name (top) + headline (bottom)
    vf = (
        f"drawbox=x=0:y=ih-100:w=iw:h=100:color=black@0.7:t=fill,"
        f"drawtext=fontfile='{font}':text='{safe_name}':fontcolor=white:"
        f"fontsize=28:x=20:y=h-85:bold=1,"
        f"drawtext=fontfile='{font}':text='{safe_headline}':fontcolor=#cccccc:"
        f"fontsize=20:x=20:y=h-50"
    )

    cmd = ["ffmpeg", "-y", "-i", str(input_mp4), "-vf", vf, "-c:a", "copy", str(output_mp4)]
    subprocess.run(cmd, check=True, capture_output=True)


def concat_segments(segments: list[Path], output: Path) -> None:
    """Concatenate a list of MP4 files into one output file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        for seg in segments:
            f.write(f"file '{seg.resolve()}'\n")
        list_file = Path(f.name)

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(list_file),
        "-c", "copy",
        str(output),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    list_file.unlink(missing_ok=True)


def assemble_broadcast(
    segments: list[dict],
    output: Path,
    show_title: str = "AI News Now",
) -> Path:
    """
    segments: list of dicts with keys:
        mp4         Path  - raw SadTalker output
        anchor_name str   - display name (e.g. "Marcus Webb")
        headline    str   - news headline for lower-third
    Returns: final output Path
    """
    output.parent.mkdir(parents=True, exist_ok=True)
    titled_segs: list[Path] = []

    for i, seg in enumerate(segments):
        lt_path = output.parent / f"_seg_{i:02d}_lt.mp4"
        add_lower_third(
            input_mp4=seg["mp4"],
            output_mp4=lt_path,
            anchor_name=seg["anchor_name"],
            headline=seg["headline"],
        )
        titled_segs.append(lt_path)

    concat_segments(titled_segs, output)

    # clean up intermediate files
    for p in titled_segs:
        p.unlink(missing_ok=True)

    return output
