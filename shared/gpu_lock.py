"""
GPU lock — prevents MusicGen and Ollama from competing for the GB10.
Simple file-based lock. Music daemon holds it during audio generation;
book daemon holds it during Ollama inference.
"""
from __future__ import annotations

import fcntl
import os
import time
from contextlib import contextmanager
from pathlib import Path

_LOCK_PATH = Path("/opt/studio/.gpu_lock")
_TIMEOUT = 1800  # 30 min max wait before giving up


@contextmanager
def acquire(owner: str = "unknown", timeout: int = _TIMEOUT):
    """Context manager — blocks until GPU lock is available."""
    lock_file = _LOCK_PATH.open("w")
    deadline = time.time() + timeout
    while True:
        try:
            fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
            lock_file.write(f"{owner}\n{os.getpid()}\n{time.time()}\n")
            lock_file.flush()
            try:
                yield
            finally:
                fcntl.flock(lock_file, fcntl.LOCK_UN)
                lock_file.seek(0)
                lock_file.truncate()
            return
        except BlockingIOError:
            if time.time() > deadline:
                raise TimeoutError(f"GPU lock timeout after {timeout}s (owner: {owner})")
            time.sleep(10)
