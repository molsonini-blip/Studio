FROM runpod/pytorch:2.2.1-py3.10-cuda12.1.1-devel-ubuntu22.04

WORKDIR /

# System deps
RUN apt-get update -q && apt-get install -y -q \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    git \
    && rm -rf /var/lib/apt/lists/*

# Clone SadTalker
RUN git clone https://github.com/OpenTalker/SadTalker.git /sadtalker

# Python deps — numpy<2 must come first
RUN pip install --quiet "numpy<2"
RUN pip install --quiet \
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
    safetensors \
    runpod

# Patch basicsr torchvision compatibility
RUN python3 -c "\
import site, pathlib; \
[f.write_text(f.read_text().replace( \
    'from torchvision.transforms.functional_tensor import rgb_to_grayscale', \
    'from torchvision.transforms.functional import rgb_to_grayscale' \
)) for d in site.getsitepackages() \
for f in [pathlib.Path(d) / 'basicsr/data/degradations.py'] \
if f.exists() and 'functional_tensor' in f.read_text()]"

# Download SadTalker models at build time (bakes into image — fast cold starts)
# Comment this out if using a RunPod Network Volume instead
WORKDIR /sadtalker
RUN pip install --quiet -r requirements.txt 2>/dev/null || true
RUN python3 scripts/download_models.py 2>/dev/null || \
    (mkdir -p checkpoints gfpgan/weights && \
     python3 -c " \
import urllib.request; \
base = 'https://github.com/OpenTalker/SadTalker/releases/download/v0.0.2-rc/'; \
files = [ \
    'SadTalker_V0.0.2_256.safetensors', \
    'SadTalker_V0.0.2_512.safetensors', \
    'mapping_00109-model.pth.tar', \
    'mapping_00229-model.pth.tar', \
    'facevid2vid_00189-model.pth.tar', \
    'auido2exp_00300-model.pth', \
    'auido2pose_00140-model.pth', \
    'shape_predictor_68_face_landmarks.dat', \
    'epoch_20.pth', \
]; \
[urllib.request.urlretrieve(base+f, 'checkpoints/'+f) for f in files]")

WORKDIR /
COPY handler.py /handler.py

CMD ["python3", "/handler.py"]
