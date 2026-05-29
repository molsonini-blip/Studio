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

# Clone MuseTalk
RUN git clone https://github.com/TMElyralab/MuseTalk /musetalk

WORKDIR /musetalk

# MuseTalk Python requirements
RUN pip3 install --quiet -r requirements.txt

# onnxruntime-gpu for DWPose (CUDA 12.x compatible wheel)
RUN pip3 install --quiet onnxruntime-gpu --extra-index-url https://aiinfra.pkgs.visualstudio.com/PublicPackages/_packaging/onnxruntime-cuda-12/pypi/simple/

# MuseTalk imports from musetalk.*
ENV PYTHONPATH=/musetalk

# Download all pretrained models at build time (~5 GB).
# snapshot_download pulls the full TMElyralab/MuseTalk repo which contains:
#   models/musetalk/   models/whisper/   models/dwpose/
#   models/face-parse-bisenet/   models/sd-vae-ft-mse/
RUN python3 -c "\
from huggingface_hub import snapshot_download; \
print('[build] Downloading MuseTalk models (~5 GB)...'); \
snapshot_download('TMElyralab/MuseTalk', local_dir='/musetalk', ignore_patterns=['*.md']); \
print('[build] Download complete.')"

RUN pip3 install --quiet "runpod>=1.7.4"

# diffusers==0.27.2 (in MuseTalk requirements) uses cached_download which was
# removed in huggingface_hub>=0.24.0 — pin after all other installs.
RUN pip3 install --quiet "huggingface_hub==0.23.4" --force-reinstall

COPY worker/handler.py /handler.py

CMD ["python3", "/handler.py"]
