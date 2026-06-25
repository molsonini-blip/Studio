#!/usr/bin/env python3
"""
RunPod serverless handler for MusicGen (Meta AudioCraft).

Deploy this as a RunPod serverless endpoint.

Dockerfile:
  FROM pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime
  RUN pip install audiocraft scipy soundfile runpod
  COPY musicgen_handler.py /handler.py
  CMD ["python", "-u", "/handler.py"]

Input JSON:
  {
    "input": {
      "prompt": "cinematic orchestral, tense, fast tempo, strings and brass",
      "duration": 30,
      "model": "facebook/musicgen-large"
    }
  }

Output JSON:
  {
    "output": {
      "audio_base64": "<base64 WAV>",
      "duration_s": 30,
      "sample_rate": 32000
    }
  }
"""
from __future__ import annotations

import base64
import io
import runpod
import scipy.io.wavfile as wavfile
import torch

_model_cache: dict = {}


def _load_model(model_name: str):
    if model_name not in _model_cache:
        from audiocraft.models import MusicGen
        print(f"Loading {model_name} ...")
        _model_cache[model_name] = MusicGen.get_pretrained(model_name)
    return _model_cache[model_name]


def handler(job: dict) -> dict:
    inp = job.get("input", {})
    prompt = inp.get("prompt", "cinematic orchestral music")
    duration = min(int(inp.get("duration", 30)), 120)  # max 2 min
    model_name = inp.get("model", "facebook/musicgen-large")

    model = _load_model(model_name)
    model.set_generation_params(duration=duration)

    with torch.no_grad():
        wav = model.generate([prompt])  # shape: (1, channels, samples)

    wav_np = wav[0, 0].cpu().numpy()  # mono
    sample_rate = model.sample_rate

    # Encode to WAV bytes
    buf = io.BytesIO()
    wavfile.write(buf, sample_rate, wav_np)
    audio_b64 = base64.b64encode(buf.getvalue()).decode()

    return {
        "output": {
            "audio_base64": audio_b64,
            "duration_s": duration,
            "sample_rate": sample_rate,
            "prompt": prompt,
        }
    }


if __name__ == "__main__":
    runpod.serverless.start({"handler": handler})
