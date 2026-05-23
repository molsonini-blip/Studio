FROM nvidia/cuda:12.8.0-cudnn-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update -q && apt-get install -y -q \
    python3 python3-pip python3-venv \
    ffmpeg libgl1 libglib2.0-0 libsm6 libxext6 git \
    && rm -rf /var/lib/apt/lists/*

# PyTorch 2.6 with CUDA 12.8 — supports Blackwell (sm_100)
RUN pip3 install --quiet \
    torch torchvision torchaudio \
    --index-url https://download.pytorch.org/whl/cu128

# numpy<2 before SadTalker deps
RUN pip3 install --quiet "numpy<2"

RUN pip3 install --quiet \
    face_alignment imageio imageio-ffmpeg pydub librosa \
    scikit-image basicsr facexlib gfpgan resampy kornia safetensors \
    "runpod==1.7.3"

# Clone SadTalker
RUN git clone https://github.com/OpenTalker/SadTalker.git /sadtalker && \
    cd /sadtalker && pip3 install --quiet -r requirements.txt 2>/dev/null || true

# Patch basicsr torchvision incompatibility
RUN python3 -c "\
import site, pathlib; \
[f.write_text(f.read_text().replace( \
    'from torchvision.transforms.functional_tensor import rgb_to_grayscale', \
    'from torchvision.transforms.functional import rgb_to_grayscale')) \
 for d in site.getsitepackages() \
 for f in [pathlib.Path(d) / 'basicsr/data/degradations.py'] \
 if f.exists() and 'functional_tensor' in f.read_text()]"

COPY worker/handler.py /handler.py

CMD ["python3", "/handler.py"]
