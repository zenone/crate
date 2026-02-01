#!/bin/bash
# Start the Crate web UI - Auto-adapting start script

set -e  # Exit on error

# Configuration
PIDFILE=".crate_web.pid"
LOGFILE="/tmp/crate-server.log"
PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PORT=8000

cd "$PROJECT_DIR"

echo "🎵 Crate - Smart Startup"
echo "======================="
echo ""

# Graceful shutdown handler
cleanup() {
    echo ""
    echo "🛑 Shutting down Crate..."

    if [ -f "$PIDFILE" ]; then
        local pid=$(cat "$PIDFILE")

        if ps -p $pid > /dev/null 2>&1; then
            kill $pid 2>/dev/null || true

            # Wait up to 3 seconds for graceful shutdown
            for i in {1..3}; do
                if ! ps -p $pid > /dev/null 2>&1; then
                    break
                fi
                sleep 1
            done

            # Force kill if still running
            if ps -p $pid > /dev/null 2>&1; then
                kill -9 $pid 2>/dev/null || true
            fi
        fi

        rm -f "$PIDFILE"
        echo "✅ Server stopped"
    fi

    echo ""
    echo "Goodbye! 👋"
    exit 0
}

# Trap Ctrl+C (SIGINT) and SIGTERM
trap cleanup SIGINT SIGTERM

# Auto-kill any existing instances (low friction!)
echo "🔍 Checking for existing server instances..."
EXISTING_PIDS=$(ps aux | grep -E "(uvicorn.*web\.main:app|python.*web/main\.py)" | grep -v grep | awk '{print $2}')

if [ -n "$EXISTING_PIDS" ]; then
    echo "📍 Found existing server(s), stopping them automatically..."
    for pid in $EXISTING_PIDS; do
        kill $pid 2>/dev/null || true
    done
    sleep 1
    echo "✅ Cleaned up existing instances"
fi

rm -f "$PIDFILE" 2>/dev/null || true
echo ""

# Activate virtual environment
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found (.venv)"
    echo "Please create it with: python -m venv .venv"
    exit 1
fi

source .venv/bin/activate

# Find available port starting from 8000
check_port() {
    lsof -i :$1 >/dev/null 2>&1
    return $?
}

MAX_PORT=8100
while check_port $PORT; do
    echo "⚠️  Port $PORT in use, trying next port..."
    PORT=$((PORT + 1))
    if [ $PORT -gt $MAX_PORT ]; then
        echo "❌ Could not find available port in range 8000-$MAX_PORT"
        exit 1
    fi
done

# Start the server
echo "✅ Found available port: $PORT"
echo "✅ Starting Crate..."
echo ""
echo "📍 URL: http://127.0.0.1:$PORT"
echo "📝 Log: $LOGFILE"
echo ""
echo "Press Ctrl+C to stop (or use ./stop_crate_web.sh)"
echo ""

# Start uvicorn in background and save PID
python -m uvicorn web.main:app --host 127.0.0.1 --port $PORT --reload > "$LOGFILE" 2>&1 &
SERVER_PID=$!

# Save PID
echo $SERVER_PID > "$PIDFILE"

# Wait a moment and verify it started
sleep 2

if ps -p $SERVER_PID > /dev/null 2>&1; then
    echo "✅ Server started successfully!"
    echo "   PID: $SERVER_PID"
    echo "   Port: $PORT"
    echo ""
    echo "🌐 Open: http://127.0.0.1:$PORT"
    echo ""

    # Auto-open browser
    URL="http://127.0.0.1:$PORT"
    echo ""
    echo "🚀 Opening browser at: $URL"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS - open in default browser
        open "$URL" 2>&1 || echo "   (Could not auto-open - please open manually)"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        xdg-open "$URL" 2>&1 || echo "   (Could not auto-open - please open manually)"
    else
        echo "   (Auto-open not supported - please open manually)"
    fi

    echo ""
    echo "📋 Server logs (Ctrl+C to stop):"
    echo ""

    # Follow the log
    tail -f "$LOGFILE"
else
    echo "❌ Server failed to start. Check log:"
    cat "$LOGFILE"
    rm -f "$PIDFILE"
    exit 1
fi
