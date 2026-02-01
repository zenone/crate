#!/bin/bash
# Stop the Crate web UI - Auto-adapting stop script

PIDFILE=".crate_web.pid"

echo "🛑 Stopping Crate..."

# Function to find and kill server processes
find_and_kill() {
    # Match multiple patterns to catch server started any way
    PIDS=$(ps aux | grep -E "(uvicorn.*web\.main:app|python.*web/main\.py|web\.main:app)" | grep -v grep | awk '{print $2}')

    if [ -n "$PIDS" ]; then
        echo "📍 Found server process(es): $PIDS"
        for pid in $PIDS; do
            echo "   Stopping PID $pid..."
            kill $pid 2>/dev/null || true
        done
        sleep 1

        # Check if any are still running and force kill
        REMAINING=$(ps aux | grep -E "(uvicorn.*web\.main:app|python.*web/main\.py|web\.main:app)" | grep -v grep | awk '{print $2}')
        if [ -n "$REMAINING" ]; then
            echo "   Force stopping remaining processes..."
            echo "$REMAINING" | xargs kill -9 2>/dev/null || true
        fi

        echo "✅ Server stopped"
        return 0
    else
        echo "ℹ️  No server processes found"
        return 1
    fi
}

# Try PID file first (clean shutdown)
if [ -f "$PIDFILE" ]; then
    PID=$(cat "$PIDFILE")
    if ps -p $PID > /dev/null 2>&1; then
        echo "📍 Found server via PID file: $PID"
        kill $PID 2>/dev/null || true
        sleep 1

        # Force kill if needed
        if ps -p $PID > /dev/null 2>&1; then
            kill -9 $PID 2>/dev/null || true
        fi
        rm -f "$PIDFILE"
        echo "✅ Server stopped"
        exit 0
    else
        echo "⚠️  PID file exists but process $PID not running, cleaning up..."
        rm -f "$PIDFILE"
    fi
fi

# Fallback: search for processes
find_and_kill
rm -f "$PIDFILE" 2>/dev/null || true

echo ""
echo "Done."
