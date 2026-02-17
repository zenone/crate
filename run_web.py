#!/usr/bin/env python3
"""
Launch script for DJ MP3 Renamer Web UI.

Usage:
    python run_web.py
    python run_web.py --port 8080
    python run_web.py --host 0.0.0.0 --port 8000
"""

import argparse
import socket
import sys
import warnings
from pathlib import Path

# Suppress urllib3/LibreSSL warning on macOS
warnings.filterwarnings("ignore", message=".*LibreSSL.*")

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def _is_port_available(host: str, port: int) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((host, port))
        return True
    except OSError:
        return False


def _pick_fallback_port(host: str, start_port: int, max_tries: int = 25) -> int | None:
    for p in range(start_port + 1, start_port + 1 + max_tries):
        if _is_port_available(host, p):
            return p
    return None


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
    parser.add_argument(
        "--open",
        action="store_true",
        help="Open browser automatically after starting server",
    )
    parser.add_argument(
        "--no-open",
        action="store_true",
        help="Do not open browser (default behavior, kept for compatibility)",
    )
    args = parser.parse_args()

    # Premium UX: if the default port is already in use, automatically pick a nearby free port.
    requested_port = args.port
    if not _is_port_available(args.host, args.port):
        if requested_port == 8000:
            fallback = _pick_fallback_port(args.host, requested_port)
            if fallback is not None:
                args.port = fallback
                print(f"ℹ️  Port {requested_port} is already in use. Using {args.port} instead.")
            else:
                print(f"Error: Port {requested_port} is already in use, and no fallback port was found.")
                print("Tip: stop the existing server or run with --port <PORT>.")
                return 1
        else:
            print(f"Error: Port {requested_port} is already in use.")
            print("Tip: stop the existing server or run with --port <PORT>.")
            return 1

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

    # Open browser only if explicitly requested with --open
    if args.open:
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
