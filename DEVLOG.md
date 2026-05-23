# Studio Development Log

Independent development log for the Studio AI Video Imaging project.
Each entry is dated and describes work performed in that session.
Git commits provide an additional cryptographic timestamp trail.

---

## 2026-05-22 (Session 5)

**Session 5 — Portrait picks, RunPod/SadTalker pipeline**

### Work completed

- Picked final portraits for all 12 anchors (8 candidates each were pre-generated on RunPod):
  - aisha_thompson → candidate 3
  - carlos_mendez → candidate 5
  - dana_reyes → candidate 6
  - james_callahan → candidate 2
  - kevin_park → candidate 2
  - layla_hassan → candidate 7
  - marcus_webb → candidate 3
  - mei_lin_zhou → candidate 8
  - priya_nair → candidate 5
  - rachel_torres → candidate 1
  - sofia_okafor → candidate 5
  - tyler_brooks → candidate 3

- Fixed `preview_anchor.py`:
  - `_add_lower_third()`: font paths now auto-detected across Debian/RHEL/macOS/Windows;
    falls back to ffmpeg default if no system font found
  - `_sadtalker()`: output detection now diffs MP4 set before/after inference instead of
    globbing blindly — handles SadTalker's timestamp-based output naming correctly
  - Added `--static` mode: CPU-only Ken Burns zoom + audio + lower-third; outputs to
    `{anchor_id}_static_preview.mp4`; useful for pipeline testing without GPU

- Built `scripts/runpod/` pipeline (4 scripts):
  - `sync_to_pod.sh <HOST> <PORT>`: rsync Studio to a RunPod pod (excludes candidates,
    models, outputs)
  - `setup.sh`: one-shot environment setup on a fresh RunPod PyTorch pod (system pkgs,
    Python deps, SadTalker models, GPU verification)
  - `render.sh [anchor_id] [--static]`: runs preview_anchor.py on the pod; all 12 or
    single anchor; GPU or static fallback
  - `sync_from_pod.sh <HOST> <PORT>`: pulls rendered MP4s back to local machine

### RunPod workflow (to execute)

1. Rent a pod on runpod.io — **RTX 4090 or A10G** (both have ≥16GB VRAM; ~$0.39–0.74/hr)
   - Template: **RunPod PyTorch 2.x** (CUDA pre-installed)
   - Expose SSH port
2. From local machine:
   ```
   bash scripts/runpod/sync_to_pod.sh <HOST> <PORT>
   ```
3. SSH into pod, then:
   ```
   cd /workspace/studio
   bash scripts/runpod/setup.sh
   export ELEVENLABS_API_KEY=your_key
   bash scripts/runpod/render.sh        # all 12 anchors (~5 min each on A10G)
   ```
4. From local machine:
   ```
   bash scripts/runpod/sync_from_pod.sh <HOST> <PORT>
   ```
5. Terminate pod when done.

### RunPod environment fixes (discovered during execution)
- `pip install "numpy<2"` required — SadTalker incompatible with numpy 2.x
- Missing deps: `safetensors`, `kornia`, `tqdm`, `face_alignment`, `basicsr`, `gfpgan`, `librosa`, `scikit-image`, `resampy`
- `basicsr/data/degradations.py` patch: `functional_tensor` → `functional` (removed in torchvision 0.16+)
- `apt-get install ffmpeg` required (not in RunPod PyTorch base image)
- SadTalker must run with `cwd=sadtalker_dir` and absolute paths for audio/portrait/result_dir
- All fixes baked into `setup.sh` and `preview_anchor.py`

### Completed (2026-05-23)
- All 12 anchor previews rendered successfully on RunPod (RTX GPU, ~7 min total)
- Files pulled to local via scp: `data/anchors/previews/*_preview.mp4`
- SSH access established: `ssh root@213.192.2.68 -p 40105 -i ~/.ssh/id_ed25519` (direct TCP, key added to pod authorized_keys)
- Pod stopped after download

### Pending
- Review 12 preview MP4s; re-pick any portraits that don't animate well
- End-to-end pipeline: live news fetch → script → TTS → SadTalker → lower-third → output

---

## 2026-05-06 (Session 4)

**Session 4 — Anchor roster, portrait generator, ElevenLabs voices**

Designed and built the full 12-anchor news talent roster and associated tooling.

### Work completed

- Designed 12-anchor roster with full diversity across gender, ethnicity (Black,
  Hispanic, White, South Asian, East Asian, Middle Eastern, mixed race), and age (24–48)
- Each anchor has distinct on-air personality: professional with light-hearted delivery,
  ranging from Marcus Webb's dry wit to Sofia Okafor's Gen-Z energy
- Built `data/anchors/roster.json`: single source of truth for all anchor metadata
  (portrait SD prompt, ElevenLabs voice design params, lower-third colors, voice_id)
- Built `scripts/anchors/generate_portraits.py`: Stable Diffusion (Realistic Vision)
  headshot generator; 4 candidates per anchor; --pick to select final; --status overview
- Built `scripts/anchors/setup_voices.py`: ElevenLabs Voice Design API integration;
  fixed endpoint (API changed from /voice-generation/* to /text-to-voice/*);
  creates unique synthetic voice per anchor from descriptors; saves voice_id to roster.json
- Built `scripts/anchors/preview_anchor.py`: full end-to-end test clip renderer
  (TTS → SadTalker lip-sync → ffmpeg lower-third overlay)
- Created all 12 ElevenLabs voices; generated and reviewed preview MP3s — all approved
- Set up RunPod GPU rental reminder for May 15th via scheduled remote agent

### Anchor roster

| Anchor | Ethnicity | Age | Voice ID |
|---|---|---|---|
| Marcus Webb | Black/M | 42 | M48xFCmxS3NPBQYh5ULb |
| Dana Reyes | Hispanic/F | 36 | U4dpEoz08OyoatMMC0Rp |
| James Callahan | White/M | 48 | EdNMI9YSQkbdy182AsTS |
| Priya Nair | South Asian/F | 33 | rMDpXFllvlS6Mz0cMkc7 |
| Mei-Lin Zhou | East Asian/F | 39 | ePnlCBcHmcSZdTTV7pgx |
| Tyler Brooks | Mixed Black/White/M | 28 | BK8VtqB5W00pBkNngDib |
| Sofia Okafor | Mixed Nigerian/Italian/F | 25 | tGeBI95c1e4WuYjDnfZ7 |
| Carlos Mendez | Hispanic/M | 44 | EMmpMwvaMpq9krsNmudR |
| Aisha Thompson | Black/F | 29 | S9JWTyUOPQLlaPCvgcBF |
| Kevin Park | East Asian/M | 35 | 6Oy82xehxlf8lTai0e2D |
| Rachel Torres | White/F | 24 | 3BcqRuArO44AU8TdSuYa |
| Layla Hassan | Middle Eastern/F | 34 | 9iwoMQHIipOzhwuhtndH |

### Pending (waiting on GPU — RunPod May 15th)
- Portrait generation (Stable Diffusion, GPU recommended)
- End-to-end preview clip rendering (SadTalker requires GPU)

### Design decisions
- ElevenLabs Creator plan ($22/mo): 30 voice slots, 100K chars/month — sufficient
  for all 12 anchors with regular TTS use
- Voice Design API generates unique synthetic voices from text descriptors — no
  voice cloning samples needed, no real person's voice used
- Portraits will be fully synthetic (SD Realistic Vision) — no real person's likeness

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

## 2026-05-06 (Session 3)

**Session 3 — Training data pipeline: archive.org scraper, transcriber, dataset preparer**

Designed and implemented the complete training data collection pipeline for both
LLM fine-tuning (LoRA) and talking head model fine-tuning.

### Work completed

- Designed and implemented `core/training/` module (4 files):
  - `scraper.py`: Internet Archive search + download pipeline
    - `search_archive()`: multi-pass strategy targeting tvnews/tvarchive collections
      using `collection:` prefix queries; defers duration filtering post-download since
      the IA search API omits duration for TV items; handles 401/403 access-restricted
      items gracefully by skipping them
    - `download_clip()`: uses `ia.get_item()` + `item.download()` directly (yt-dlp fails
      on archive.org TV items with "No video formats found"); resolves yt-dlp/ffmpeg
      binaries via `_bin()` helper that checks PATH then venv/bin; extracts audio to
      16kHz mono WAV via ffmpeg; measures actual duration via ffprobe post-download
    - `DownloadedClip` dataclass; `collect_dataset()` orchestrator with polite 1s delay
  - `transcriber.py`: SRT caption parser + faster-whisper CPU transcription
    - Prefers existing captions; falls back to Whisper int8 quantized (CPU-optimized)
    - `transcribe_all()` batch processor
  - `preparer.py`: cleans transcripts; splits into 150-word segments; builds Alpaca/
    ShareGPT format LLM dataset JSON and talking head manifest (video+audio+transcript)
  - `face_extractor.py`: OpenCV Haar cascade anchor frame extraction; single-face filter;
    `frames_index.json` manifest

- Designed and implemented training scripts:
  - `scripts/training/train_llm.py`: LoRA fine-tune via PEFT on Alpaca dataset;
    GPU-required check with cloud rental suggestions; saves adapter + Modelfile for
    `ollama create`
  - `scripts/training/train_talking_head.py`: FOMM and SadTalker fine-tune paths;
    GPU-required check; clones First Order Motion Model repo on first run
  - `scripts/training/collect_data.py`: 5-step orchestration (download → transcribe →
    LLM dataset → TH manifest → face frames); full CLI argument set

- Debugged archive.org scraper through several iterations:
  - `num_found` → `params={"rows": N}` (API change in internetarchive v5)
  - Collection filter AND query returning 0 results → switched to prefix queries
  - Duration filtering too aggressive (all TV episodes are 30-60 min) → raised default
    from 300s to 7200s; defer filtering to download time
  - `ia.download()` passing kwargs to `get_item()` → use `item_obj.download()` directly
  - Major network items (FOXNEWS, CBS) are 401/403 restricted → skip in download;
    search returns public-domain items (sept_11_tv_archive, community archives)
  - Confirmed end-to-end: 3 clips downloaded successfully on server with audio extracted

- Uploaded all training code to StatsDBServer01 `/opt/studio/` via SFTP

### Design decisions

- LLM fine-tuning (train_llm.py) and talking head fine-tuning (train_talking_head.py)
  both require GPU — server is CPU-only; scripts exit gracefully with instructions
  pointing to cloud GPU rental (~$0.39/hr RunPod A10G)
- archive.org TV episodes are full 30-60 min broadcasts; `preparer.py` segments them
  into 150-word training examples — no need to find pre-segmented clips
- faster-whisper with int8 quantization is the CPU-viable transcription option;
  full Whisper would be prohibitively slow on the server
- SRT captions preferred over Whisper when available (ground truth vs. ASR errors)

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
