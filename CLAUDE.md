# Studio — AI Content Production Platform

## What this project is
A multi-division AI content production platform. Each division has its own Ollama-powered
idea generator and production pipeline.

**Divisions:**
- **News Anchor** — automated AI anchor: RSS → Ollama → TTS → lip-sync video
- **Music** — soundtrack & song ideas by genre → audio generation pipeline
- **Books** — romance series generator → chapter writer → EPUB/PDF
- **Shorts** — YouTube/social short-form content (AngryACGuy HVAC channel)
- **Movie** — Hollywood-style film production (Jim Hall documentary project)

## Project root
`C:\Users\molson\OneDrive\Documents\AI Projects\Studio` (OneDrive — syncs across machines)

## Architecture
```
shared/
  ollama.py       # shared Ollama client — all pipelines import from here

music/
  ideas.py        # Ollama idea generator — soundtracks + all genres
  pipeline.py     # audio generation scaffold (Suno/Udio/MusicGen TBD)
  genres/         # soundtracks/, rock/, country/, hip_hop/, electronic/, jazz/, classical/, pop/
  projects/       # saved idea JSON files

books/
  romance/
    ideas.py            # Ollama series/book concept generator (20-book series)
    chapter_generator.py # full chapter writer — resumes on interrupt
    epub_builder.py     # assembles EPUB or PDF from generated chapters
    series/             # series concept JSON files
    output/             # generated chapters + final EPUBs/PDFs

shorts/
  angry_ac_guy/
    ideas.py        # Ollama episode idea generator
    pipeline.py     # script → TTS → video scaffold
    episodes/       # episode idea batches + produced episode folders

movie/
  jim_hall/
    pipeline.py     # full Jim Hall movie pipeline (was scripts/jim_hall_movie.py)
    render_gpu.py   # RunPod GPU render (was scripts/jim_hall_render_gpu.py)
    scenes.py       # 24-scene screenplay
    narrator.py     # Ollama narration refinement
    producer.py     # production coordinator
    renderer.py     # image/video renderer
  ideas.py          # Ollama movie concept generator
  projects/         # movie concept JSON files

news_anchor (existing):
core/
  news/           # RSS/API fetcher, Ollama bias-filter, SRT formatter
  pipelines/      # video_gen, face_swap, talking_head (MuseTalk)
  processing/     # video frame I/O, lower-third compositing
  training/       # archive.org scraper, Whisper transcriber, dataset preparer
  models/         # ModelManager singleton
web/              # FastAPI server (deployed to EdgeExpert)
desktop/          # PySide6 desktop app
scripts/
  anchors/        # generate_portraits.py, setup_voices.py, preview_anchor.py
  runpod/         # sync_to_pod.sh, setup.sh, render.sh, sync_from_pod.sh
data/anchors/
  roster.json     # single source of truth — 12 anchors
  portraits/      # {anchor_id}.png
  voices/         # {anchor_id}_preview.mp3
  previews/       # {anchor_id}_preview.mp4
config/settings.yaml
```

## The 12 anchors
All portraits picked, all ElevenLabs voices created and confirmed.

| Anchor | ID | Voice ID |
|---|---|---|
| Marcus Webb | marcus_webb | M48xFCmxS3NPBQYh5ULb |
| Dana Reyes | dana_reyes | U4dpEoz08OyoatMMC0Rp |
| James Callahan | james_callahan | EdNMI9YSQkbdy182AsTS |
| Priya Nair | priya_nair | rMDpXFllvlS6Mz0cMkc7 |
| Mei-Lin Zhou | mei_lin_zhou | ePnlCBcHmcSZdTTV7pgx |
| Tyler Brooks | tyler_brooks | BK8VtqB5W00pBkNngDib |
| Sofia Okafor | sofia_okafor | tGeBI95c1e4WuYjDnfZ7 |
| Carlos Mendez | carlos_mendez | EMmpMwvaMpq9krsNmudR |
| Aisha Thompson | aisha_thompson | S9JWTyUOPQLlaPCvgcBF |
| Kevin Park | kevin_park | 6Oy82xehxlf8lTai0e2D |
| Rachel Torres | rachel_torres | 3BcqRuArO44AU8TdSuYa |
| Layla Hassan | layla_hassan | 9iwoMQHIipOzhwuhtndH |

## Infrastructure
- **EdgeExpert** (MSI EdgeXpert — all execution happens here, NOTHING runs locally on Windows)
  - Hostname: edgexpert-672f | Tailscale: 100.86.243.19 | LAN: 10.0.0.39
  - OS: DGX OS / Ubuntu 24.04 Arm64 | RAM: 121 GB | Storage: 3.7 TB
  - GPU: NVIDIA GB10 Grace Blackwell (built-in — RunPod not needed for GPU work)
  - SSH: `ssh edgeexpert` → uses ~/.ssh/id_ed25519, user molson
  - Projects: `/home/molson/projects/studio/` | Venv: `venv/` | Logs: `logs/`
  - Running: Ollama (llama3.2:3b, localhost:11434), Tony Scott research daemon
- **RunPod**: Available if needed for additional GPU burst (RTX 4090 / A10G)
- **ElevenLabs**: Creator plan, 30 voice slots, 100K chars/month

## Key env vars
```
ELEVENLABS_API_KEY   — TTS generation
NEWSAPI_KEY          — newsapi.org (optional, RSS works without)
GNEWS_KEY            — gnews.io (optional)
```

## Common commands
```bash
# Test preview pipeline (CPU, no GPU needed)
python scripts/anchors/preview_anchor.py --anchor marcus_webb --static

# Full SadTalker preview (GPU required — run on RunPod)
python scripts/anchors/preview_anchor.py --anchor marcus_webb

# Portrait status
python scripts/anchors/generate_portraits.py --status

# Full pipeline status
python scripts/anchors/preview_anchor.py --status

# Start web server (on CPU server)
uvicorn web.main:app --host 0.0.0.0 --port 8000
```

## Common commands
```bash
# --- MUSIC ---
# Generate 5 soundtrack ideas
python -m music.ideas --genre soundtracks --context "gritty 1970s detective thriller" --count 5

# Generate full soundtrack brief
python -m music.ideas --soundtrack --context "World War II drama" --save my_wwii_film

# --- BOOKS ---
# Generate a 20-book romance series
python -m books.romance.ideas --series --theme "small-town firefighters" --save firefighter_series

# Write all chapters for book 1
python -m books.romance.chapter_generator --series books/romance/series/firefighter_series.json --book 1

# Build EPUB
python -m books.romance.epub_builder --series books/romance/series/firefighter_series.json --book 1

# --- SHORTS (AngryACGuy) ---
# Generate episode ideas
python -m shorts.angry_ac_guy.ideas --count 5 --save batch_01

# Run episode pipeline
python -m shorts.angry_ac_guy.pipeline --episode shorts/angry_ac_guy/episodes/batch_01.json

# --- MOVIE ---
# Generate new movie concepts
python -m movie.ideas --genre drama --count 3

# Jim Hall pipeline (on CPU server)
python movie/jim_hall/pipeline.py

# --- NEWS ANCHOR (original) ---
python scripts/anchors/preview_anchor.py --anchor marcus_webb --static
uvicorn web.main:app --host 0.0.0.0 --port 8000
```

## Current state (as of 2026-06-24)
- **News anchor**: 12 portraits + voices done; previews not yet rendered
- **Music**: ideas.py + pipeline scaffold built; audio tool (Suno/Udio/MusicGen) not yet wired in
- **Books**: romance pipeline built (ideas → chapters → EPUB); no series started yet
- **Shorts**: AngryACGuy ideas + pipeline scaffold built; TTS/video not yet wired in
- **Movie**: Jim Hall files consolidated to movie/jim_hall/; pipeline intact

## Next milestones
1. Pick a music audio backend (Suno API, Udio, or local MusicGen) and wire into music/pipeline.py
2. Generate first romance series concept and write Book 1
3. Generate first AngryACGuy episode batch and produce Episode 1
4. Render 12 news anchor preview clips on RunPod
