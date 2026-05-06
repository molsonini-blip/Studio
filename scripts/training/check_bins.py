import sys, shutil
from pathlib import Path

for name in ("yt-dlp", "ffmpeg", "ffprobe"):
    found = shutil.which(name)
    venv = Path(sys.executable).parent / name
    print(f"{name}: which={found}  venv={venv}  venv_exists={venv.exists()}")
