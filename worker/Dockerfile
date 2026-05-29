FROM runpod/pytorch:2.2.1-py3.10-cuda12.1.1-devel-ubuntu22.04

RUN apt-get update -q && apt-get install -y -q \
    ffmpeg libgl1 libglib2.0-0 libsm6 libxext6 git git-lfs \
    && git lfs install \
    && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/TMElyralab/MuseTalk /musetalk

RUN pip install --quiet -r /musetalk/requirements.txt && \
    pip install --quiet onnxruntime-gpu \
        --extra-index-url https://aiinfra.pkgs.visualstudio.com/PublicPackages/_packaging/onnxruntime-cuda-12/pypi/simple/ && \
    pip install --quiet runpod && \
    pip install --quiet "huggingface_hub==0.23.4" --force-reinstall

ENV PYTHONPATH=/musetalk

# Models (~5 GB). Two deployment options:
#
#   Option A — Bake into image (slow build, fast cold start):
#     docker build --build-arg BAKE_MODELS=1 -t studio-musetalk-worker .
#
#   Option B — RunPod Network Volume (recommended for production):
#     1. Create a Network Volume in RunPod (10 GB+)
#     2. Spin up a temp GPU pod with the volume mounted at /musetalk/models
#     3. Run: python3 /download_models.py
#     4. Configure the serverless endpoint to mount that volume at /musetalk/models
ARG BAKE_MODELS=0
COPY download_models.py /download_models.py
RUN if [ "$BAKE_MODELS" = "1" ]; then python3 /download_models.py; fi

COPY handler.py /handler.py

CMD ["python3", "/handler.py"]
