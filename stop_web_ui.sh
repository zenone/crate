#!/bin/bash
# Stop the DJ MP3 Renamer web UI

PIDFILE=".dj_renamer_web.pid"

echo "🛑 Stopping DJ MP3 Renamer..."
echo ""

if [ ! -f "$PIDFILE" ]; then
    echo "⚠️  No PID file found - server may not be running"
    echo ""
    # Try to find and kill any running instances anyway
    PIDS=$(ps aux | grep "uvicorn.*web.main:app" | grep -v grep | awk '{print $2}')
    if [ -n "$PIDS" ]; then
        echo "Found running instances, stopping them..."
        echo "$PIDS" | xargs kill 2>/dev/null || true
        sleep 1
        echo "✓ Stopped orphaned instances"
    else
        echo "No running instances found"
    fi
    exit 0
fi

PID=$(cat "$PIDFILE")

if ! ps -p $PID > /dev/null 2>&1; then
    echo "⚠️  Process $PID is not running"
    rm -f "$PIDFILE"
    exit 0
fi

echo "Stopping PID: $PID"
kill $PID 2>/dev/null || true

# Wait for graceful shutdown
sleep 2

# Check if still running
if ps -p $PID > /dev/null 2>&1; then
    echo "Force stopping..."
    kill -9 $PID 2>/dev/null || true
fi

rm -f "$PIDFILE"

echo "✅ Server stopped successfully"
