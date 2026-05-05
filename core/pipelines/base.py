from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class BasePipeline(ABC):
    """Common interface every Studio pipeline must implement."""

    name: str = "base"

    def __init__(self) -> None:
        self._loaded = False

    # ------------------------------------------------------------------
    @abstractmethod
    def load(self) -> None:
        """Download / load model weights into memory."""

    @abstractmethod
    def unload(self) -> None:
        """Release model weights and free VRAM."""

    @abstractmethod
    def run(self, **kwargs: Any) -> Any:
        """Execute the pipeline and return results."""

    # ------------------------------------------------------------------
    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def __enter__(self) -> "BasePipeline":
        self.load()
        return self

    def __exit__(self, *_: Any) -> None:
        self.unload()

    # ------------------------------------------------------------------
    @staticmethod
    def _ensure_dir(path: Path | str) -> Path:
        p = Path(path)
        p.mkdir(parents=True, exist_ok=True)
        return p
