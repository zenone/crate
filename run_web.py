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
import warnings
from pathlib import Path

# Suppress urllib3/LibreSSL warning on macOS
warnings.filterwarnings("ignore", message=".*LibreSSL.*")

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

    print("🎵 DJ MP3 Renamer Web UI")

    # Check for SSL certs.
    # NOTE: Having cert files present is not enough — they must be browser-trusted.
    # For the smoothest non-technical UX, prefer HTTP by default. The helper script
    # start_crate_web.sh can provision mkcert-trusted HTTPS.
    ssl_enabled = False
    ssl_keyfile = project_root / "certs" / "localhost-key.pem"
    ssl_certfile = project_root / "certs" / "localhost.pem"

    if ssl_keyfile.exists() and ssl_certfile.exists():
        # Trust is handled by mkcert -install; if the user hasn't installed the CA,
        # browsers will warn. We intentionally keep ssl_enabled=False here and
        # let start_crate_web.sh manage trusted HTTPS.
        ssl_enabled = False

    protocol = "https" if ssl_enabled else "http"
    print(f"📡 Starting server at {protocol}://{args.host}:{args.port}")
    if ssl_enabled:
        print("🔒 HTTPS enabled")
    else:
        print("🔓 HTTPS disabled (default). For trusted HTTPS, run: ./start_crate_web.sh")

    print("✨ Press Ctrl+C to stop")
    print()

    # Open browser automatically
    try:
        import webbrowser
        webbrowser.open(f"{protocol}://{args.host}:{args.port}")
    except Exception:
        pass

    # Build uvicorn args
    uvicorn_args = {
        "app": "web.main:app",
        "host": args.host,
        "port": args.port,
        "reload": args.reload,
        "log_level": "info",
    }

    if ssl_enabled:
        uvicorn_args["ssl_keyfile"] = str(ssl_keyfile)
        uvicorn_args["ssl_certfile"] = str(ssl_certfile)

    uvicorn.run(**uvicorn_args)

    return 0


if __name__ == "__main__":
    sys.exit(main())
