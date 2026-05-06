from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import torch
import yaml


def _load_config() -> dict:
    cfg_path = Path(__file__).resolve().parents[2] / "config" / "settings.yaml"
    with open(cfg_path) as f:
        return yaml.safe_load(f)


def resolve_device(preferred: str = "cuda") -> torch.device:
    if preferred == "cuda" and torch.cuda.is_available():
        return torch.device("cuda")
    if preferred == "mps" and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def resolve_dtype(dtype_str: str) -> torch.dtype:
    return {"float16": torch.float16, "bfloat16": torch.bfloat16, "float32": torch.float32}.get(
        dtype_str, torch.float16
    )


class ModelManager:
    """Central registry for loaded pipeline models.

    Caches instances by key so pipelines share weights across requests
    rather than reloading each time.
    """

    def __init__(self) -> None:
        cfg = _load_config()
        self.device = resolve_device(cfg["device"]["preferred"])
        self.dtype = resolve_dtype(cfg["device"]["dtype"])
        self.models_dir = Path(__file__).resolve().parents[3] / cfg["paths"]["models_dir"]
        self.cache_dir = Path(__file__).resolve().parents[3] / cfg["paths"]["cache_dir"]
        os.makedirs(self.cache_dir, exist_ok=True)
        os.environ.setdefault("HF_HOME", str(self.cache_dir))
        self._registry: dict[str, Any] = {}

    # ------------------------------------------------------------------
    def register(self, key: str, model: Any) -> None:
        self._registry[key] = model

    def get(self, key: str) -> Any | None:
        return self._registry.get(key)

    def is_loaded(self, key: str) -> bool:
        return key in self._registry

    def unload(self, key: str) -> None:
        if key in self._registry:
            del self._registry[key]
            if self.device.type == "cuda":
                torch.cuda.empty_cache()

    def unload_all(self) -> None:
        self._registry.clear()
        if self.device.type == "cuda":
            torch.cuda.empty_cache()

    # ------------------------------------------------------------------
    def model_path(self, *parts: str) -> Path:
        return self.models_dir.joinpath(*parts)


# Singleton — import and use `manager` directly in pipelines
manager = ModelManager()
