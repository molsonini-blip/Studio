#!/bin/bash
# RunPod GPU setup for Studio anchor portrait + preview generation.
# Run this once on a fresh pod from /workspace/studio.
#
# Assumes: RunPod PyTorch template (CUDA + torch pre-installed)
# Tested on: runpod/pytorch:2.2.1-py3.10-cuda12.1.1-devel-ubuntu22.04
#
# Usage (from /workspace/studio):
#   bash scripts/runpod_setup.sh

set -e

echo "=== Studio RunPod Setup ==="

# ── 1. System packages ─────────────────────────────────────────────────────────
echo ""
echo "[1/4] Installing system packages..."
apt-get update -qq
apt-get install -y --no-install-recommends \
    ffmpeg \
    libsm6 libxext6 libgl1 \
    fonts-dejavu \
    libportaudio2 \
    wget curl git \
    > /dev/null
echo "  Done."

# ── 2. Python dependencies ─────────────────────────────────────────────────────
# RunPod PyTorch image already has torch+CUDA — install everything else.
echo ""
echo "[2/4] Installing Python dependencies (skipping torch — pre-installed)..."
pip install -q --upgrade pip
pip install -q \
    diffusers>=0.27.0 \
    transformers>=4.40.0 \
    accelerate>=0.29.0 \
    safetensors>=0.4.0 \
    einops>=0.7.0 \
    omegaconf>=2.3.0 \
    xformers \
    insightface>=0.7.3 \
    onnxruntime-gpu>=1.17.0 \
    opencv-python>=4.9.0 \
    moviepy>=1.0.3 \
    ffmpeg-python>=0.2.0 \
    imageio[ffmpeg]>=2.34.0 \
    Pillow>=10.2.0 \
    scikit-image>=0.22.0 \
    librosa>=0.10.0 \
    soundfile>=0.12.0 \
    fastapi>=0.110.0 \
    uvicorn[standard]>=0.29.0 \
    python-multipart>=0.0.9 \
    requests>=2.31.0 \
    tqdm>=4.66.0 \
    huggingface-hub>=0.22.0 \
    pyyaml>=6.0.1 \
    python-dotenv>=1.0.0 \
    numpy>=1.26.0
echo "  Done."

# ── 3. SadTalker ──────────────────────────────────────────────────────────────
echo ""
echo "[3/4] Downloading SadTalker checkpoints + inference scripts..."
python scripts/download_models.py --sadtalker
echo "  Done."

# ── 4. GPU check ───────────────────────────────────────────────────────────────
echo ""
echo "[4/4] Verifying GPU..."
python - <<'EOF'
import torch, sys
if not torch.cuda.is_available():
    print("  ERROR: CUDA not available. Wrong pod template?")
    sys.exit(1)
print(f"  GPU: {torch.cuda.get_device_name(0)}")
print(f"  VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
print(f"  torch: {torch.__version__}")
EOF

echo ""
echo "=== Setup complete ==="
echo ""
echo "Next steps:"
echo "  1. Generate portraits (4 candidates per anchor):"
echo "       python scripts/anchors/generate_portraits.py"
echo ""
echo "  2. Check candidates in data/anchors/portraits/ and pick finals:"
echo "       python scripts/anchors/generate_portraits.py --status"
echo "       python scripts/anchors/generate_portraits.py --pick <anchor_id> <1-4>"
echo ""
echo "  3. Render preview clips (needs ELEVENLABS_API_KEY):"
echo "       export ELEVENLABS_API_KEY=your_key_here"
echo "       python scripts/anchors/preview_anchor.py --all"
echo ""
echo "  4. Download previews from pod to local machine:"
echo "       runpodctl receive <code>  (from your local machine)"
