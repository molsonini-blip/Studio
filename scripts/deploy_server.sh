#!/usr/bin/env bash
# Deploy Studio to StatsDBServer01 via git pull.
#
# Run from your LOCAL machine (Git Bash):
#   bash scripts/deploy_server.sh
#
# First-time setup on the server is automatic.
# After that, just push to GitHub and run this script to deploy.

set -euo pipefail

SERVER="root@162.251.146.56"
KEY="$HOME/.ssh/id_ed25519"
REPO="https://github.com/molsonini-blip/Studio.git"
REMOTE="/opt/studio"

echo "=== Studio deploy → StatsDBServer01 ==="

ssh -i "$KEY" "$SERVER" bash <<REMOTE
set -e

git config --global --add safe.directory "$REMOTE" 2>/dev/null || true

if [ ! -d "$REMOTE/.git" ]; then
  echo "[setup] Initialising git in existing directory..."
  mkdir -p "$REMOTE"
  cd "$REMOTE"
  git init
  git remote add origin "$REPO"
  git fetch origin
  git checkout -f -t origin/master || git reset --hard origin/master
  echo "[setup] Done."
else
  echo "[pull] Updating from GitHub..."
  cd "$REMOTE"
  git remote get-url origin &>/dev/null || git remote add origin "$REPO"
  git fetch origin
  git reset --hard origin/master
fi

cd "$REMOTE"

# Create venv if needed
if [ ! -d .venv ]; then
  echo "[setup] Creating .venv..."
  python3 -m venv .venv
fi

# Install/update Python deps
echo "[deps] Installing Python deps..."
.venv/bin/pip install --quiet --upgrade pip
.venv/bin/pip install --quiet requests paramiko python-dotenv

echo ""
echo "Deploy complete. Run:"
echo "  cd $REMOTE && .venv/bin/python scripts/produce.py"
REMOTE
