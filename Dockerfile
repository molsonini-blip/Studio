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

# Hallo Python requirements (diffusers, xformers, insightface, mediapipe, etc.)
RUN pip3 install --quiet -r requirements.txt

# diffusers==0.27.2 imports cached_download which was removed in huggingface_hub>=0.24.0.
# Force-pin back to the last compatible version after requirements may have upgraded it.
RUN pip3 install --quiet "huggingface_hub==0.23.4" --force-reinstall

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

COPY worker/handler.py /handler.py

CMD ["python3", "/handler.py"]
