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
    """Scale to 1280x720 studio composite with lower-third overlay."""
    font = _find_font()
    safe_name = anchor_name.replace("'", "\\'")
    safe_headline = (
        headline[:70]
        .replace("\\", "\\\\")
        .replace("'", "\\'")
        .replace(":", "\\:")
        .replace(",", "\\,")
    )

    # Layout (1280x720):
    #   Portrait  : 560x560, x=360-920, y=20-580  (centered, 20px top margin)
    #   Side cols : x=0-360 and x=920-1280         (studio walls)
    #   Desk      : y=576-720                       (covers portrait bottom edge)
    #   Lower 3rd : y=614-720
    vf = ",".join([
        "scale=560:560:force_original_aspect_ratio=decrease",
        "pad=1280:720:(ow-iw)/2:20:color=0x07101a",
        # Studio side columns
        "drawbox=x=0:y=0:w=360:h=580:color=0x0b1426:t=fill",
        "drawbox=x=357:y=0:w=3:h=580:color=0x1a3050:t=fill",
        "drawbox=x=920:y=0:w=360:h=580:color=0x0b1426:t=fill",
        "drawbox=x=920:y=0:w=3:h=580:color=0x1a3050:t=fill",
        # Top accent bar
        "drawbox=x=0:y=0:w=1280:h=3:color=0x1e4070:t=fill",
        # Desk surface (overlaps portrait bottom slightly — desk in front of anchor)
        "drawbox=x=0:y=576:w=1280:h=144:color=0x0c1820:t=fill",
        "drawbox=x=20:y=574:w=1240:h=3:color=0x1e3a60:t=fill",
        # Network bug — top right
        "drawbox=x=1170:y=10:w=100:h=26:color=0x091525:t=fill",
        f"drawtext=fontfile='{font}':text='AI NEWS':fontcolor=0x3377bb:fontsize=15:x=1178:y=16",
        # Lower third
        "drawbox=x=0:y=614:w=1280:h=106:color=0x04070e:t=fill",
        "drawbox=x=0:y=614:w=1280:h=4:color=0x2448a0:t=fill",
        f"drawtext=fontfile='{font}':text='{safe_name}':fontcolor=white:fontsize=40:x=40:y=626",
        f"drawtext=fontfile='{font}':text='{safe_headline}':fontcolor=#8899bb:fontsize=26:x=40:y=674",
    ])

    cmd = ["ffmpeg", "-y", "-i", str(input_mp4), "-vf", vf, "-c:a", "copy", str(output_mp4)]
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"ffmpeg lower-third failed (rc={result.returncode}):\n"
            f"{result.stderr.decode(errors='replace')[-2000:]}"
        )


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
    result = subprocess.run(cmd, capture_output=True)
    list_file.unlink(missing_ok=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"ffmpeg concat failed (rc={result.returncode}):\n"
            f"{result.stderr.decode(errors='replace')[-2000:]}"
        )


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
