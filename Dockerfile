FROM runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04

RUN apt-get update -q && apt-get install -y -q \
    ffmpeg libgl1 libglib2.0-0 libsm6 libxext6 git \
    && rm -rf /var/lib/apt/lists/*

# Clone SadTalker repo (no models yet — downloaded at first job)
RUN git clone https://github.com/OpenTalker/SadTalker.git /sadtalker

RUN pip install --quiet "numpy<2" && \
    pip install --quiet \
      face_alignment imageio imageio-ffmpeg pydub librosa \
      scikit-image basicsr facexlib gfpgan resampy kornia safetensors \
      "runpod==1.7.3" && \
    cd /sadtalker && pip install --quiet -r requirements.txt 2>/dev/null || true

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
