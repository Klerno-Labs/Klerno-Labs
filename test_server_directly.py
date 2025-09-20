#!/usr/bin/env python3
"""Direct server test to diagnose shutdown issue."""

import subprocess
import sys
import threading
import time
from pathlib import Path

import requests


def test_direct_api():
    """Test the API directly using requests."""
    print("Testing FastAPI server directly...")

    # Change to the correct directory
    os.chdir(Path(__file__).parent)

    # Start server in background
    server_process = subprocess.Popen([
        sys.executable, "-m", "uvicorn",
        "app.main:app",
        "--host", "127.0.0.1",
        "--port", "8001"
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    # Wait for server to start
    time.sleep(3)

    try:
        # Test health endpoint
        response = requests.get("http://127.0.0.1:8001/health", timeout=5)
        print(f"Health endpoint status: {response.status_code}")
        print(f"Health response: {response.text}")

        # Test status endpoint
        response = requests.get("http://127.0.0.1:8001/status", timeout=5)
        print(f"Status endpoint status: {response.status_code}")
        print(f"Status response: {response.text}")

        # Test docs
        response = requests.get("http://127.0.0.1:8001/docs", timeout=5)
        print(f"Docs endpoint status: {response.status_code}")

    except Exception as e:
        print(f"Error testing endpoints: {e}")

    finally:
        # Clean shutdown
        server_process.terminate()
        try:
            server_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server_process.kill()

if __name__ == "__main__":
    import os
    test_direct_api()
