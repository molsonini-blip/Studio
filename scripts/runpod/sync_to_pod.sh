#!/usr/bin/env bash
# Push Studio project to a RunPod pod.
# Usage: bash scripts/runpod/sync_to_pod.sh <HOST> <PORT>
#   HOST and PORT come from RunPod's SSH connection string.
#
# Example:
#   bash scripts/runpod/sync_to_pod.sh 213.173.96.12 12345

set -euo pipefail

HOST="${1:?Usage: sync_to_pod.sh <HOST> <PORT>}"
PORT="${2:?Usage: sync_to_pod.sh <HOST> <PORT>}"
REMOTE="root@${HOST}"
REMOTE_DIR="/workspace/studio"
KEY="${RUNPOD_SSH_KEY:-$HOME/.ssh/id_rsa}"

echo "Syncing Studio → ${REMOTE}:${REMOTE_DIR} (port ${PORT})"

rsync -avz --progress \
  -e "ssh -p ${PORT} -i ${KEY} -o StrictHostKeyChecking=no" \
  --exclude=".git" \
  --exclude="__pycache__" \
  --exclude="*.pyc" \
  --exclude="models/sadtalker"       \
  --exclude="models/wav2lip"         \
  --exclude="outputs/" \
  --exclude="data/anchors/portraits/*_candidate_*.png" \
  "$(git -C "$(dirname "$0")/../.." rev-parse --show-toplevel)/" \
  "${REMOTE}:${REMOTE_DIR}/"

echo "Sync complete."
echo "Next: ssh -p ${PORT} -i ${KEY} ${REMOTE}"
echo "      cd ${REMOTE_DIR} && bash scripts/runpod/setup.sh"
