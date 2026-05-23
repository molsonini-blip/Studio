#!/usr/bin/env bash
# Render anchor preview clips on RunPod (with SadTalker lip-sync).
# Must have run setup.sh first and set ELEVENLABS_API_KEY.
#
# Usage (from /workspace/studio):
#   bash scripts/runpod/render.sh                 # all 12 anchors
#   bash scripts/runpod/render.sh marcus_webb     # single anchor
#   bash scripts/runpod/render.sh --static        # Ken Burns fallback (no GPU needed)

set -euo pipefail
STUDIO_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$STUDIO_DIR"

if [ -z "${ELEVENLABS_API_KEY:-}" ]; then
  echo "ERROR: ELEVENLABS_API_KEY is not set."
  echo "  export ELEVENLABS_API_KEY=your_key"
  exit 1
fi

ANCHOR="${1:-}"
STATIC_FLAG=""

if [ "$ANCHOR" = "--static" ]; then
  STATIC_FLAG="--static"
  ANCHOR=""
fi

if [ -n "$ANCHOR" ]; then
  echo "Rendering: $ANCHOR"
  python scripts/anchors/preview_anchor.py --anchor "$ANCHOR" $STATIC_FLAG
else
  echo "Rendering all 12 anchors..."
  python scripts/anchors/preview_anchor.py --all $STATIC_FLAG
fi

echo ""
echo "Previews saved to: data/anchors/previews/"
ls -lh data/anchors/previews/*.mp4 2>/dev/null || echo "  (none yet)"
