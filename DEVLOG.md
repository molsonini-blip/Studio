# Studio Development Log

Independent development log for the Studio AI Video Imaging project.
Each entry is dated and describes work performed in that session.
Git commits provide an additional cryptographic timestamp trail.

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
