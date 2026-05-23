#!/usr/bin/env bash
# Pull rendered preview MP4s from RunPod back to local machine.
# Usage: bash scripts/runpod/sync_from_pod.sh <HOST> <PORT>

set -euo pipefail

HOST="${1:?Usage: sync_from_pod.sh <HOST> <PORT>}"
PORT="${2:?Usage: sync_from_pod.sh <HOST> <PORT>}"
REMOTE="root@${HOST}"
KEY="${RUNPOD_SSH_KEY:-$HOME/.ssh/id_rsa}"
LOCAL_DIR="$(git -C "$(dirname "$0")/../.." rev-parse --show-toplevel)/data/anchors/previews"

mkdir -p "$LOCAL_DIR"

echo "Pulling previews from ${REMOTE}:${PORT} → ${LOCAL_DIR}"

rsync -avz --progress \
  -e "ssh -p ${PORT} -i ${KEY} -o StrictHostKeyChecking=no" \
  "${REMOTE}:/workspace/studio/data/anchors/previews/" \
  "${LOCAL_DIR}/"

echo "Done. Files:"
ls -lh "${LOCAL_DIR}"/*.mp4 2>/dev/null || echo "  (none)"
