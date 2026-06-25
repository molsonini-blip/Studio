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
#   ssh edgeexpert tail -f /opt/studio/logs/tony_scott_research.log
#
# Stop:
#   ssh edgeexpert kill $(cat /opt/studio/logs/tony_scott_research.pid)

SERVER="edgeexpert"        # Update with actual hostname/IP if needed
REMOTE_DIR="/opt/studio"
PYTHON="python3"

echo "=== Deploying Tony Scott research daemon to $SERVER ==="

# Sync project files to server
rsync -avz --exclude='.git' --exclude='venv' --exclude='__pycache__' \
    "$(pwd)/" "$SERVER:$REMOTE_DIR/"

echo ""
echo "=== Installing dependencies on $SERVER ==="
ssh "$SERVER" "
    cd $REMOTE_DIR
    pip3 install duckduckgo-search httpx 2>&1 | tail -5

    # Create log directory
    mkdir -p /opt/studio/logs

    # Seed the registry with known sources
    PYTHONPATH=$REMOTE_DIR $PYTHON -m movie.tony_scott.sources.registry --seed

    # Kill any existing research daemon
    if [ -f /opt/studio/logs/tony_scott_research.pid ]; then
        OLD_PID=\$(cat /opt/studio/logs/tony_scott_research.pid)
        kill \$OLD_PID 2>/dev/null && echo 'Stopped previous daemon (PID '\$OLD_PID')'
        rm -f /opt/studio/logs/tony_scott_research.pid
    fi

    echo ''
    echo '=== Starting research daemon ==='
    nohup $PYTHON -m movie.tony_scott.research_loop \
        --interval 2700 \
        > /opt/studio/logs/tony_scott_research.log 2>&1 &

    sleep 2
    if [ -f /opt/studio/logs/tony_scott_research.pid ]; then
        echo 'Daemon started. PID: '\$(cat /opt/studio/logs/tony_scott_research.pid)
    else
        echo 'Daemon may have started. Check the log.'
    fi
    echo 'Log: /opt/studio/logs/tony_scott_research.log'
"

echo ""
echo "=== Done. Monitor with: ==="
echo "  ssh $SERVER tail -f /opt/studio/logs/tony_scott_research.log"
