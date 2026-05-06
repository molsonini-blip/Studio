from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import torch
import yaml

from core.models.manager import manager
from core.pipelines.base import BasePipeline


def _cfg() -> dict:
    p = Path(__file__).resolve().parents[2] / "config" / "settings.yaml"
    with open(p) as f:
        return yaml.safe_load(f)["video_generation"]


@dataclass
class VideoGenRequest:
    prompt: str
    negative_prompt: str = ""
    pipeline: str = "animatediff"   # animatediff | stable_video_diffusion | cogvideox
    num_frames: int = 16
    fps: int = 8
    width: int = 512
    height: int = 512
    guidance_scale: float = 7.5
    num_inference_steps: int = 25
    seed: int = -1
    # image-to-video only
    init_image: Path | None = None
    motion_strength: float = 0.8


@dataclass
class VideoGenResult:
    frames: list[Any]              # list of PIL.Image
    fps: int
    pipeline_used: str
    output_path: Path | None = None


class AnimateDiffPipeline(BasePipeline):
    name = "animatediff"

    def load(self) -> None:
        if self._loaded:
            return
        from diffusers import AnimateDiffPipeline, DDIMScheduler, MotionAdapter
        from diffusers.utils import export_to_gif

        cfg = _cfg()["pipelines"]["animatediff"]
        adapter = MotionAdapter.from_pretrained(
            cfg["motion_adapter_id"], cache_dir=str(manager.cache_dir)
        )
        pipe = AnimateDiffPipeline.from_pretrained(
            cfg["base_model_id"],
            motion_adapter=adapter,
            torch_dtype=manager.dtype,
            cache_dir=str(manager.cache_dir),
        )
        pipe.scheduler = DDIMScheduler.from_config(pipe.scheduler.config, beta_schedule="linear")
        pipe.enable_vae_slicing()
        if manager.device.type == "cuda":
            pipe.enable_model_cpu_offload()
        else:
            pipe = pipe.to(manager.device)

        manager.register("animatediff", pipe)
        self._loaded = True

    def unload(self) -> None:
        manager.unload("animatediff")
        self._loaded = False

    def run(self, req: VideoGenRequest) -> VideoGenResult:
        self.load()
        pipe = manager.get("animatediff")
        generator = torch.Generator(device=manager.device)
        if req.seed >= 0:
            generator.manual_seed(req.seed)

        output = pipe(
            prompt=req.prompt,
            negative_prompt=req.negative_prompt,
            num_frames=req.num_frames,
            width=req.width,
            height=req.height,
            guidance_scale=req.guidance_scale,
            num_inference_steps=req.num_inference_steps,
            generator=generator,
        )
        return VideoGenResult(frames=output.frames[0], fps=req.fps, pipeline_used=self.name)


class StableVideoDiffusionPipeline(BasePipeline):
    name = "stable_video_diffusion"

    def load(self) -> None:
        if self._loaded:
            return
        from diffusers import StableVideoDiffusionPipeline as SVDPipe

        cfg = _cfg()["pipelines"]["stable_video_diffusion"]
        pipe = SVDPipe.from_pretrained(
            cfg["repo_id"],
            torch_dtype=manager.dtype,
            variant="fp16",
            cache_dir=str(manager.cache_dir),
        )
        pipe.enable_model_cpu_offload()
        manager.register("svd", pipe)
        self._loaded = True

    def unload(self) -> None:
        manager.unload("svd")
        self._loaded = False

    def run(self, req: VideoGenRequest) -> VideoGenResult:
        from PIL import Image

        self.load()
        if req.init_image is None:
            raise ValueError("StableVideoDiffusion requires an init_image.")
        pipe = manager.get("svd")
        image = Image.open(req.init_image).convert("RGB").resize((req.width, req.height))
        generator = torch.Generator(device="cpu")
        if req.seed >= 0:
            generator.manual_seed(req.seed)

        output = pipe(
            image,
            num_frames=req.num_frames,
            motion_bucket_id=int(req.motion_strength * 127),
            noise_aug_strength=0.02,
            generator=generator,
        )
        return VideoGenResult(frames=output.frames[0], fps=req.fps, pipeline_used=self.name)


class CogVideoXPipeline(BasePipeline):
    name = "cogvideox"

    def load(self) -> None:
        if self._loaded:
            return
        from diffusers import CogVideoXPipeline

        cfg = _cfg()["pipelines"]["cogvideox"]
        pipe = CogVideoXPipeline.from_pretrained(
            cfg["repo_id"],
            torch_dtype=torch.bfloat16,
            cache_dir=str(manager.cache_dir),
        )
        pipe.enable_model_cpu_offload()
        pipe.vae.enable_slicing()
        pipe.vae.enable_tiling()
        manager.register("cogvideox", pipe)
        self._loaded = True

    def unload(self) -> None:
        manager.unload("cogvideox")
        self._loaded = False

    def run(self, req: VideoGenRequest) -> VideoGenResult:
        self.load()
        pipe = manager.get("cogvideox")
        generator = torch.Generator(device="cpu")
        if req.seed >= 0:
            generator.manual_seed(req.seed)

        output = pipe(
            prompt=req.prompt,
            negative_prompt=req.negative_prompt or None,
            num_videos_per_prompt=1,
            num_inference_steps=req.num_inference_steps,
            num_frames=req.num_frames,
            guidance_scale=req.guidance_scale,
            generator=generator,
        )
        return VideoGenResult(frames=output.frames[0], fps=req.fps, pipeline_used=self.name)


# Factory
_PIPELINES: dict[str, type[BasePipeline]] = {
    "animatediff": AnimateDiffPipeline,
    "stable_video_diffusion": StableVideoDiffusionPipeline,
    "cogvideox": CogVideoXPipeline,
}

_instances: dict[str, BasePipeline] = {}


def get_pipeline(name: str) -> BasePipeline:
    if name not in _instances:
        cls = _PIPELINES.get(name)
        if cls is None:
            raise ValueError(f"Unknown video generation pipeline: {name!r}")
        _instances[name] = cls()
    return _instances[name]


def generate(req: VideoGenRequest) -> VideoGenResult:
    pipeline = get_pipeline(req.pipeline)
    return pipeline.run(req)
