# Studio Development Log

Independent development log for the Studio AI Video Imaging project.
Each entry is dated and describes work performed in that session.
Git commits provide an additional cryptographic timestamp trail.

---

## 2026-05-06

**Session 2 — News pipeline, server deployment, and service configuration**

Deployed Studio backend to StatsDBServer01 (162.251.146.56, Ubuntu 26.04 LTS, CPU-only Intel Xeon SapphireRapids, 15GB RAM, 99GB disk).

### Work completed

- Connected to remote server via paramiko (password auth); added SSH public key to
  `/root/.ssh/authorized_keys` for future key-based access
- Installed system packages: git, curl, wget, build-essential, python3-venv, python3-dev,
  libgl1, libglib2.0-0, ffmpeg, libsm6, libxext6, libffi-dev
- Uploaded full Studio project to `/opt/studio/` via SFTP (28 files)
- Created Python venv at `/opt/studio/venv`; installed all deps with CPU-only torch
  (torch 2.11.0+cpu, diffusers 0.38.0, fastapi 0.136.1, insightface 0.7.3, trafilatura 2.0.0)
- Installed Ollama v0.23.1 as a systemd service; pulled `llama3.2:3b` (2GB, CPU mode)
- Designed and implemented `core/news/` module (4 files):
  - `models.py`: `RawArticle`, `ProcessedScript`, `CaptionLine` dataclasses
  - `fetcher.py`: RSS (7 major outlets: AP, Reuters, BBC, NPR, CBS, ABC, USA Today),
    NewsAPI.org, and GNews sources; `trafilatura` full-text extraction; combined
    `fetch_articles()` with URL deduplication and date sort; API keys via env vars
  - `processor.py`: Ollama/llama3.2:3b LLM pipeline — strips political bias, opinion,
    loaded language, attribution framing; rewrites as short declarative fact-only
    sentences at 7th grade reading level; temperature=0.1 for deterministic output;
    JSON-structured prompt with strict editorial rules; fallback on parse failure
  - `formatter.py`: splits into broadcast sentences; wraps to 42-char SRT lines timed
    at 130 wpm anchor pace; generates full SRT caption string
- Implemented `web/routers/news.py` with three endpoints:
  - `GET /api/news/headlines` — fetch from all sources, optional keyword/category filter
  - `POST /api/news/process` — fetch single URL, bias-filter, return broadcast script + SRT
  - `POST /api/news/process-batch` — batch fetch + process top headlines
- Wired news router into `web/main.py`; added `news:` section to `config/settings.yaml`
- Fixed `parents[3]` → `parents[2]` config path bug across all `core/` modules
- Created `/etc/systemd/system/studio.service` (uvicorn, 2 workers, auto-restart on failure)
- Created `/opt/studio/.env` for NEWSAPI_KEY and GNEWS_KEY (RSS works with no keys)
- Service confirmed active; `/health` → `{"status":"ok"}` and `/api/news/headlines` returning live headlines

### Design decisions

- `llama3.2:3b` chosen for CPU server — 2GB footprint, fast enough for text processing
- Strict LLM prompt with temperature=0.1 ensures deterministic, fact-only rewrites
- RSS feeds require no API keys — pipeline is fully functional without any credentials;
  NewsAPI and GNews are additive via `.env` for broader coverage
- SRT timing derived from word count at 130 wpm (broadcast anchor delivery pace)
- 42 chars/line follows broadcast captioning standard (FCC compliant)
- Video generation pipelines deployed but will run slowly without GPU — flagged for
  future hardware upgrade if video generation at scale is required

---

## 2026-05-05

**Session 1 — Project scaffolding and core pipeline design**

Established the Studio project from scratch. All code written independently.

### Work completed

- Created `c:\Users\molson\OneDrive\Documents\Studio` as the project root
- Initialized git repository
- Authored `requirements.txt`: torch, diffusers, transformers, insightface, opencv,
  mediapipe, moviepy, fastapi, uvicorn, PySide6, huggingface-hub, and supporting libs
- Authored `config/settings.yaml`: device config (CUDA/MPS/CPU), all three pipeline
  configs (video gen, face swap, talking head), web server, and desktop app settings

- Designed and implemented `core/models/manager.py`:
  - `ModelManager` singleton: device/dtype resolution, model registry, cache dir management
  - `resolve_device()` and `resolve_dtype()` helpers for hardware-agnostic loading

- Designed and implemented `core/pipelines/base.py`:
  - `BasePipeline` abstract class: `load()`, `unload()`, `run()` interface
  - Context manager support so pipelines can be used as `with` blocks

- Designed and implemented `core/pipelines/video_gen.py`:
  - `AnimateDiffPipeline`: text-to-video via HuggingFace diffusers AnimateDiff
  - `StableVideoDiffusionPipeline`: image-to-video via SVD-XT
  - `CogVideoXPipeline`: high-quality text-to-video via CogVideoX-5B (bfloat16)
  - Factory `generate(req)` function; pipelines are cached as singletons
  - `VideoGenRequest` / `VideoGenResult` dataclasses

- Designed and implemented `core/pipelines/face_swap.py`:
  - `FaceSwapPipeline`: InsightFace detection + inswapper_128.onnx replacement
  - Supports both image and video targets; frame-by-frame video processing
  - Optional GFPGAN post-enhancement; configurable blend alpha
  - `FaceSwapRequest` / `FaceSwapResult` dataclasses

- Designed and implemented `core/pipelines/talking_head.py`:
  - `SadTalkerPipeline`: audio-driven portrait animation; calls upstream SadTalker
    inference.py as subprocess (avoids forking the repo)
  - `Wav2LipPipeline`: lip-sync for existing video sources via Wav2Lip GAN
  - `still_mode=True` reduces head motion for professional anchor appearance
  - `TalkingHeadRequest` / `TalkingHeadResult` dataclasses

- Designed and implemented `core/processing/video.py`:
  - Frame I/O: `frames_from_video()`, `frames_to_video()`, `pil_frames_to_video()`
  - Metadata: `video_info()`
  - Compositing: `overlay_image()`, `add_lower_third()` (news-anchor graphic burn-in)
  - `extract_thumbnail()`

- Designed and implemented `web/main.py` (FastAPI server):
  - CORS middleware, static file serving, health endpoint
  - Three routers mounted at `/api/video-gen`, `/api/face-swap`, `/api/talking-head`

- Designed and implemented `web/routers/video_gen.py`, `face_swap.py`, `talking_head.py`:
  - File upload endpoints using `UploadFile`; job-ID-based result retrieval
  - Pydantic request/response models

- Designed and implemented `web/static/index.html`:
  - Dark-themed single-page app with three tabbed panels
  - Video Generation, Face Swap, and News Anchor tabs with full parameter controls
  - Pure HTML/CSS/JS (no framework dependency)

- Designed and implemented PySide6 desktop app:
  - `desktop/main.py`: dark palette, Fusion style, app entry point
  - `desktop/windows/main_window.py`: tabbed `QMainWindow`
  - `desktop/widgets/video_gen_widget.py`: prompt + parameter form, threaded generation
  - `desktop/widgets/face_swap_widget.py`: file pickers, alpha slider, threaded swap
  - `desktop/widgets/talking_head_widget.py`: portrait + audio pickers, model options

- Implemented `scripts/download_models.py`:
  - `--face-swap`: inswapper_128.onnx + GFPGANv1.4.pth
  - `--sadtalker`: SadTalker checkpoints from HuggingFace + repo clone
  - `--wav2lip`: Wav2Lip GAN checkpoint + repo clone
  - `--all`: downloads everything

### Design decisions

- Local-only inference — no cloud API calls, no usage restrictions
- Three-pipeline architecture (video gen, face swap, talking head) designed to be
  composable: e.g., generate a scene → face-swap the anchor → animate with audio
- SadTalker and Wav2Lip invoked via subprocess to isolate their dependency trees
- `ModelManager` singleton prevents reloading weights between requests
- Web and desktop share the same `core/` pipeline code — no duplication
- `still_mode=True` default on TalkingHead for anchor-appropriate minimal motion
- `add_lower_third()` utility in video.py enables news-broadcast graphic overlays
