#!/usr/bin/env python3
"""
Launch script for DJ MP3 Renamer Web UI.

Usage:
    python run_web.py
    python run_web.py --port 8080
    python run_web.py --host 0.0.0.0 --port 8000
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def main():
    parser = argparse.ArgumentParser(description="Launch DJ MP3 Renamer Web UI")
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind to (default: 8000)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development",
    )
    args = parser.parse_args()

    try:
        import uvicorn
    except ImportError:
        print("Error: uvicorn not installed.")
        print("Install with: pip install -r requirements-web.txt")
        return 1

    print(f"🎵 DJ MP3 Renamer Web UI")
    print(f"📡 Starting server at http://{args.host}:{args.port}")
    print(f"✨ Press Ctrl+C to stop")
    print()

    uvicorn.run(
        "web.server:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info",
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
