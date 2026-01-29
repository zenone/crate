#!/bin/bash
# Start the DJ MP3 Renamer web UI

echo "🎵 Starting DJ MP3 Renamer Web UI..."
echo ""

# Activate virtual environment
source .venv/bin/activate

# Start uvicorn server
echo "Starting server on http://127.0.0.1:8000"
echo "Press Ctrl+C to stop"
echo ""

python -m uvicorn web.main:app --host 127.0.0.1 --port 8000 --reload
