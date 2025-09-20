#!/usr/bin/env python3
"""
Klerno Labs Development Server Script
====================================

Simple script to start the development server with proper configuration.

Usage:
    python dev-server.py [options]

Options:
    --port PORT    Port to run on (default: 8001)
    --host HOST    Host to bind to (default: 127.0.0.1)
    --reload       Enable auto-reload (default: True)
"""

import argparse
import subprocess
import sys


def main():
    """Start the development server."""
    parser = argparse.ArgumentParser(description="Start Klerno Labs development server")
    parser.add_argument("--port", type=int, default=8001, help="Port to run on")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--no-reload", action="store_true", help="Disable auto-reload")

    args = parser.parse_args()

    print("🚀 Starting Klerno Labs Development Server")
    print(f"📍 Server will be available at: http://{args.host}:{args.port}")
    print("⚡ Auto-reload enabled" if not args.no_reload else "📡 Auto-reload disabled")
    print("🛑 Press Ctrl+C to stop the server")
    print("-" * 50)

    reload_flag = "--reload" if not args.no_reload else ""
    cmd = f"python -m uvicorn app.main:app --host {args.host} --port {args.port} {reload_flag}".strip()

    try:
        subprocess.run(cmd, shell=True)
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Failed to start server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
