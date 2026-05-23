# Studio — AI News Anchor Video Platform

## What this project is
Fully automated AI news anchor system: fetches live headlines, rewrites them to broadcast standard, generates TTS audio via ElevenLabs, animates a synthetic anchor portrait with SadTalker lip-sync, and burns in a lower-third graphic overlay.

## Project root
`C:\Users\olson\OneDrive\Documents\Studio` (OneDrive — syncs across machines)

## Architecture
```
core/
  news/           # RSS/API fetcher, Ollama bias-filter, SRT formatter
  pipelines/      # video_gen, face_swap, talking_head (SadTalker/Wav2Lip)
  processing/     # video frame I/O, lower-third compositing
  training/       # archive.org scraper, Whisper transcriber, dataset preparer
  models/         # ModelManager singleton
web/              # FastAPI server (deployed to StatsDBServer01)
desktop/          # PySide6 desktop app
scripts/
  anchors/        # generate_portraits.py, setup_voices.py, preview_anchor.py
  training/       # collect_data.py, train_llm.py, train_talking_head.py
  runpod/         # sync_to_pod.sh, setup.sh, render.sh, sync_from_pod.sh
  download_models.py
data/anchors/
  roster.json     # single source of truth — 12 anchors with voice IDs + prompts
  portraits/      # {anchor_id}.png = final; {anchor_id}_candidate_N.png = drafts
  voices/         # {anchor_id}_preview.mp3
  previews/       # {anchor_id}_preview.mp4 (SadTalker) or _static_preview.mp4
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
- **CPU server**: StatsDBServer01, 162.251.146.56, Ubuntu, `/opt/studio/`
  - SSH: `ssh -i ~/.ssh/ffl_server root@162.251.146.56`
  - Running: FastAPI (uvicorn, port 8000), Ollama (llama3.2:3b)
- **GPU**: RunPod (rent as needed — RTX 4090 or A10G, ~$0.39–0.74/hr)
  - Workflow: `sync_to_pod.sh` → `setup.sh` → `render.sh` → `sync_from_pod.sh`
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

## Current state (as of 2026-05-22)
- All 12 portraits: **picked** (final PNGs exist)
- All 12 voices: **created** (ElevenLabs voice IDs in roster.json, preview MP3s exist)
- Previews (lip-synced MP4s): **not yet rendered** on this machine
  - May exist on another computer or RunPod from a prior session
  - Check `data/anchors/previews/` — if empty, run RunPod workflow above

## Next milestone
Render all 12 anchor preview clips → review → wire up live news pipeline end-to-end.
