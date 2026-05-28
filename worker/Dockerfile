FROM runpod/pytorch:2.2.1-py3.10-cuda12.1.1-devel-ubuntu22.04

# System deps
RUN apt-get update -q && apt-get install -y -q \
    ffmpeg libgl1 libglib2.0-0 libsm6 libxext6 git git-lfs \
    && rm -rf /var/lib/apt/lists/*

# Clone Hallo
RUN git lfs install && \
    git clone https://github.com/fudan-generative-vision/hallo.git /hallo

# Install Hallo Python deps + RunPod SDK
RUN pip install --quiet -r /hallo/requirements.txt && \
    pip install --quiet runpod huggingface_hub

# Models (~15 GB total). Two deployment options:
#
#   Option A — Bake into image (slow build, fast cold start):
#     docker build --build-arg BAKE_MODELS=1 -t studio-hallo-worker .
#
#   Option B — RunPod Network Volume (recommended for production):
#     1. Create a Network Volume in RunPod (20 GB+)
#     2. Spin up a temp GPU pod with the volume mounted at /hallo/pretrained_models
#     3. Run: python3 /download_models.py
#     4. Configure the serverless endpoint to mount that volume at /hallo/pretrained_models
ARG BAKE_MODELS=0
COPY download_models.py /download_models.py
RUN if [ "$BAKE_MODELS" = "1" ]; then python3 /download_models.py; fi

COPY handler.py /handler.py

CMD ["python3", "/handler.py"]
