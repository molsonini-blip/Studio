FROM runpod/pytorch:2.2.1-py3.10-cuda12.1.1-devel-ubuntu22.04

# System deps
RUN apt-get update -q && apt-get install -y -q \
    ffmpeg libgl1 libglib2.0-0 libsm6 libxext6 git \
    && rm -rf /var/lib/apt/lists/*

# Clone SadTalker
RUN git clone https://github.com/OpenTalker/SadTalker.git /sadtalker

# numpy<2 must come before everything else
RUN pip install --quiet "numpy<2"

# SadTalker Python deps
RUN pip install --quiet \
    face_alignment imageio imageio-ffmpeg pydub librosa \
    scikit-image basicsr facexlib gfpgan resampy kornia safetensors runpod

# Patch basicsr torchvision incompatibility
RUN python3 -c "\
import site, pathlib; \
[f.write_text(f.read_text().replace( \
    'from torchvision.transforms.functional_tensor import rgb_to_grayscale', \
    'from torchvision.transforms.functional import rgb_to_grayscale')) \
 for d in site.getsitepackages() \
 for f in [pathlib.Path(d) / 'basicsr/data/degradations.py'] \
 if f.exists() and 'functional_tensor' in f.read_text()]"

# Install SadTalker's own deps
RUN cd /sadtalker && pip install --quiet -r requirements.txt 2>/dev/null || true

# Copy handler
COPY handler.py /handler.py

# Models download at first run via handler._ensure_models()
# To pre-cache models, mount a RunPod Network Volume at /sadtalker/checkpoints

CMD ["python3", "/handler.py"]
