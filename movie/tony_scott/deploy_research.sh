#!/bin/bash
# Deploy Tony Scott research daemon to EdgeExpert server.
#
# Run this once to get the daemon running indefinitely.
# It searches the web every 45 min, adds sources to the registry, never stops.
#
# Usage (from your local machine):
#   bash movie/tony_scott/deploy_research.sh
#
# Monitor:
#   ssh edgeexpert "tail -f ~/projects/studio/logs/tony_scott_research.log"
#
# Stop:
#   ssh edgeexpert "kill \$(cat ~/projects/studio/logs/tony_scott_research.pid)"

SERVER="edgeexpert"
REMOTE_DIR="$HOME/projects/studio"
PYTHON="python3"

echo "=== Deploying Tony Scott research daemon to $SERVER ==="

# Sync project files to server
rsync -avz --exclude='.git' --exclude='venv' --exclude='__pycache__' \
    "$(pwd)/" "$SERVER:$REMOTE_DIR/"

echo ""
echo "=== Installing dependencies on $SERVER ==="
ssh "$SERVER" "
    cd $REMOTE_DIR
    pip3 install duckduckgo-search httpx --quiet 2>&1 | grep -v '^Collecting\|^  Down\|^  Inst\|^  Using\|^Already'

    # Create log directory
    mkdir -p $REMOTE_DIR/logs

    # Seed the registry with known sources
    PYTHONPATH=$REMOTE_DIR $PYTHON -m movie.tony_scott.sources.registry --seed

    # Kill any existing research daemon
    if [ -f $REMOTE_DIR/logs/tony_scott_research.pid ]; then
        OLD_PID=\$(cat $REMOTE_DIR/logs/tony_scott_research.pid)
        kill \$OLD_PID 2>/dev/null && echo 'Stopped previous daemon (PID '\$OLD_PID')'
        rm -f $REMOTE_DIR/logs/tony_scott_research.pid
    fi

    echo ''
    echo '=== Starting research daemon ==='
    cd $REMOTE_DIR
    nohup $PYTHON -m movie.tony_scott.research_loop \
        --interval 2700 \
        > $REMOTE_DIR/logs/tony_scott_research.log 2>&1 &

    echo \$! > $REMOTE_DIR/logs/tony_scott_research.pid
    sleep 2
    echo 'Daemon started. PID: '\$(cat $REMOTE_DIR/logs/tony_scott_research.pid)
    echo 'Log: $REMOTE_DIR/logs/tony_scott_research.log'
"

echo ""
echo "=== Done. Monitor with: ==="
echo "  ssh $SERVER 'tail -f ~/projects/studio/logs/tony_scott_research.log'"
