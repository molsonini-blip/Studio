FROM nvidia/cuda:12.1.1-cudnn8-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

RUN apt-get update -q && apt-get install -y -q \
    python3 python3-pip \
    ffmpeg libgl1 libglib2.0-0 libsm6 libxext6 git git-lfs \
    && git lfs install \
    && rm -rf /var/lib/apt/lists/*

# PyTorch 2.2.2 + CUDA 12.1 — A100/Ampere (sm_80)
RUN pip3 install --quiet \
    torch==2.2.2 torchvision==0.17.2 torchaudio==2.2.2 \
    --index-url https://download.pytorch.org/whl/cu121

# Clone Hallo
RUN git clone https://github.com/fudan-generative-vision/hallo /hallo

WORKDIR /hallo

# Hallo Python requirements (diffusers, insightface, mediapipe, etc.)
RUN pip3 install --quiet -r requirements.txt

# Install Hallo itself as a Python package (scripts import from hallo.*)
RUN pip3 install -e .

# PYTHONPATH ensures 'import hallo' works even if editable install is incomplete
ENV PYTHONPATH=/hallo

# Download ALL pretrained models at build time.
# The single HuggingFace repo contains every model Hallo needs:
#   hallo/  stable-diffusion-v1-5/  motion_module/  face_analysis/
#   wav2vec/  audio_separator/  sd-vae-ft-mse/
RUN python3 -c "\
from huggingface_hub import snapshot_download; \
print('[build] Downloading Hallo models (~15 GB)...'); \
snapshot_download('fudan-generative-ai/hallo', local_dir='/hallo/pretrained_models'); \
print('[build] Download complete.')"

RUN pip3 install --quiet "runpod>=1.7.4"

# Must be last — diffusers==0.27.2 needs cached_download removed in huggingface_hub>=0.24.0.
# Pin after all other installs so nothing can upgrade it again.
RUN pip3 install --quiet "huggingface_hub==0.23.4" --force-reinstall

COPY worker/handler.py /handler.py

CMD ["python3", "/handler.py"]
