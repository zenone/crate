#!/bin/bash
# Start the DJ MP3 Renamer web UI with smart instance management

set -e  # Exit on error

# Configuration
PIDFILE=".dj_renamer_web.pid"
LOGFILE="/tmp/dj_renamer_web.log"
PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

cd "$PROJECT_DIR"

# Graceful shutdown handler
cleanup() {
    echo ""
    echo "🛑 Shutting down DJ MP3 Renamer..."

    if [ -f "$PIDFILE" ]; then
        local pid=$(cat "$PIDFILE")

        # Send SIGTERM for graceful shutdown
        if ps -p $pid > /dev/null 2>&1; then
            kill $pid 2>/dev/null || true

            # Wait up to 5 seconds for graceful shutdown
            for i in {1..5}; do
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

        # Clean up PID file
        rm -f "$PIDFILE"
        echo "✓ Server stopped gracefully"
        echo "✓ PID file cleaned up"
    else
        echo "✓ Server stopped"
    fi

    echo ""
    echo "Goodbye! 👋"
    exit 0
}

# Trap Ctrl+C (SIGINT) and SIGTERM
trap cleanup SIGINT SIGTERM

echo "🎵 DJ MP3 Renamer - Smart Startup"
echo "================================"
echo ""

# Function to check if a port is in use
check_port() {
    lsof -i :$1 >/dev/null 2>&1
    return $?
}

# Function to check if the process is still running
is_running() {
    if [ -f "$PIDFILE" ]; then
        local pid=$(cat "$PIDFILE")
        if ps -p $pid > /dev/null 2>&1; then
            # Verify it's actually our uvicorn process
            if ps -p $pid | grep -q "uvicorn.*web.main:app"; then
                return 0  # Running
            fi
        fi
        # PID file exists but process is dead - clean up
        rm -f "$PIDFILE"
    fi
    return 1  # Not running
}

# Function to get the port from a running instance
get_running_port() {
    if [ -f "$PIDFILE" ]; then
        local pid=$(cat "$PIDFILE")
        local port=$(lsof -p $pid -a -i4 -sTCP:LISTEN -Fn | grep -oE ':[0-9]+' | tr -d ':' | head -1)
        echo "$port"
    fi
}

# Function to stop existing instance
stop_instance() {
    if [ -f "$PIDFILE" ]; then
        local pid=$(cat "$PIDFILE")
        echo "🛑 Stopping existing instance (PID: $pid)..."
        kill $pid 2>/dev/null || true
        sleep 1
        # Force kill if still running
        if ps -p $pid > /dev/null 2>&1; then
            kill -9 $pid 2>/dev/null || true
        fi
        rm -f "$PIDFILE"
        echo "✓ Stopped"
        echo ""
    fi
}

# Check if already running
if is_running; then
    RUNNING_PORT=$(get_running_port)
    echo "⚠️  DJ MP3 Renamer is already running!"
    echo ""
    echo "Running on: http://127.0.0.1:$RUNNING_PORT"
    echo "PID: $(cat $PIDFILE)"
    echo ""
    echo "Options:"
    echo "  1. Open http://127.0.0.1:$RUNNING_PORT in your browser"
    echo "  2. Stop it with: ./stop_web_ui.sh"
    echo "  3. Force restart with: ./start_web_ui.sh --force"
    echo ""

    # Check for --force flag
    if [ "$1" = "--force" ] || [ "$1" = "-f" ]; then
        echo "🔄 Force restart requested..."
        stop_instance
    else
        exit 0
    fi
fi

# Activate virtual environment
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found (.venv)"
    echo "Please create it with: python -m venv .venv"
    exit 1
fi

source .venv/bin/activate

# Find available port starting from 8000
PORT=8000
MAX_PORT=8100

while check_port $PORT; do
    echo "⚠️  Port $PORT is already in use (different app)"
    PORT=$((PORT + 1))
    if [ $PORT -gt $MAX_PORT ]; then
        echo "❌ Could not find available port in range 8000-$MAX_PORT"
        exit 1
    fi
done

# Start the server
echo "✓ Found available port: $PORT"
echo "✓ Starting DJ MP3 Renamer..."
echo ""
echo "📍 URL: http://127.0.0.1:$PORT"
echo "📝 Log: $LOGFILE"
echo ""
echo "Press Ctrl+C to stop (or use ./stop_web_ui.sh)"
echo ""

# Start uvicorn in background and save PID
python -m uvicorn web.main:app --host 127.0.0.1 --port $PORT --reload > "$LOGFILE" 2>&1 &
SERVER_PID=$!

# Save PID to file
echo $SERVER_PID > "$PIDFILE"

# Wait a moment and verify it started
sleep 2

if ps -p $SERVER_PID > /dev/null 2>&1; then
    echo "✅ Server started successfully!"
    echo "   PID: $SERVER_PID"
    echo "   Port: $PORT"
    echo ""
    echo "🌐 Open in browser: http://127.0.0.1:$PORT"
    echo ""

    # Follow the log
    tail -f "$LOGFILE"
else
    echo "❌ Server failed to start. Check log:"
    cat "$LOGFILE"
    rm -f "$PIDFILE"
    exit 1
fi
