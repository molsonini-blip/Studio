#!/usr/bin/env bash
# Run this ONCE on a fresh RunPod pod (PyTorch template recommended).
# Sets up Studio + SadTalker models. Takes ~10 min on first run.
#
# Usage (from /workspace/studio):
#   bash scripts/runpod/setup.sh

set -euo pipefail
STUDIO_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$STUDIO_DIR"

echo "=== Studio RunPod Setup ==="
echo "Working dir: $STUDIO_DIR"

# ── System packages ───────────────────────────────────────────────────────────
echo "[1/4] Installing system packages..."
apt-get update -q
apt-get install -y -q \
  ffmpeg \
  libgl1 \
  libglib2.0-0 \
  libsm6 \
  libxext6 \
  fonts-dejavu \
  git \
  2>/dev/null

# ── Python deps ───────────────────────────────────────────────────────────────
echo "[2/4] Installing Python packages..."
# RunPod PyTorch template ships torch+cuda — reinstall Studio deps on top of it
pip install --quiet --upgrade pip
pip install --quiet \
  diffusers \
  transformers \
  accelerate \
  huggingface_hub \
  insightface \
  onnxruntime-gpu \
  opencv-python-headless \
  moviepy \
  fastapi \
  uvicorn \
  requests \
  tqdm \
  pillow

# SadTalker-specific deps
pip install --quiet "numpy<2"
pip install --quiet \
  face_alignment \
  imageio \
  imageio-ffmpeg \
  pydub \
  librosa \
  scikit-image \
  basicsr \
  facexlib \
  gfpgan \
  resampy \
  kornia \
  safetensors

# Patch basicsr's broken torchvision import (functional_tensor removed in torchvision 0.16+)
python3 -c "
import site, pathlib
for d in site.getsitepackages():
    f = pathlib.Path(d) / 'basicsr/data/degradations.py'
    if f.exists():
        txt = f.read_text()
        if 'functional_tensor' in txt:
            f.write_text(txt.replace(
                'from torchvision.transforms.functional_tensor import rgb_to_grayscale',
                'from torchvision.transforms.functional import rgb_to_grayscale'
            ))
            print(f'Patched: {f}')
        break
"

echo "[2/4] Done."

# ── SadTalker repo + models ───────────────────────────────────────────────────
echo "[3/4] Downloading SadTalker..."
python scripts/download_models.py --sadtalker

# Install SadTalker's own requirements (torch-based extras it needs)
if [ -f "models/sadtalker/requirements.txt" ]; then
  pip install --quiet -r models/sadtalker/requirements.txt 2>/dev/null || true
fi
echo "[3/4] Done."

# ── Verify GPU ────────────────────────────────────────────────────────────────
echo "[4/4] Checking GPU..."
python - <<'EOF'
import torch
if torch.cuda.is_available():
    name = torch.cuda.get_device_name(0)
    vram = torch.cuda.get_device_properties(0).total_memory / 1024**3
    print(f"  GPU: {name}  ({vram:.1f} GB VRAM) ✓")
else:
    print("  WARNING: CUDA not available — SadTalker will be very slow")
EOF

echo ""
echo "=== Setup complete ==="
echo ""
echo "Next steps:"
echo "  export ELEVENLABS_API_KEY=your_key"
echo "  bash scripts/runpod/render.sh               # all 12 anchors"
echo "  bash scripts/runpod/render.sh marcus_webb   # single anchor"
