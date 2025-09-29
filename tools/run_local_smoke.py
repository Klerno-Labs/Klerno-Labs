"""Run a local smoke flow end-to-end for developers.

Steps:
 - seed local SQLite DB
 - start the app with uvicorn in a subprocess
 - wait for /ready to return 200
 - run tools/login_probe.py --save-token
 - run tools/prod_smoke_test.py against the server using saved tokens
 - stop the server and print a summary

Usage:
  python tools/run_local_smoke.py
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUN_DIR = ROOT / ".run"
RUN_DIR.mkdir(exist_ok=True)


def seed_db() -> None:
    print("Seeding local DB...")
    subprocess.check_call([sys.executable, str(ROOT / "tools" / "seed_local_db.py")])


def start_server() -> subprocess.Popen:
    print("Starting uvicorn server in background...")
    # Run uvicorn with the app's entrypoint; adapt if your entrypoint differs
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        "8000",
    ]
    proc = subprocess.Popen(cmd, cwd=str(ROOT), stdout=sys.stdout, stderr=sys.stderr)
    return proc


def wait_for_ready(timeout: int = 30) -> bool:
    import requests

    url = "http://127.0.0.1:8000/ready"
    print(f"Waiting for {url} (timeout {timeout}s) ...")
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = requests.get(url, timeout=2)
            if r.status_code == 200:
                print("/ready OK")
                return True
        except Exception:
            pass
        time.sleep(0.5)
    print("Timed out waiting for /ready")
    return False


def run_login_probe() -> int:
    print("Running login_probe to acquire tokens...")
    return subprocess.call(
        [sys.executable, str(ROOT / "tools" / "login_probe.py"), "--save-token"]
    )  # returns 0 on success


def run_prod_smoke() -> int:
    print("Running prod_smoke_test against http://127.0.0.1:8000 ...")
    cmd = [
        sys.executable,
        str(ROOT / "tools" / "prod_smoke_test.py"),
        "--url",
        "http://127.0.0.1:8000",
        "--token-file",
        str(RUN_DIR / "dev_tokens.json"),
    ]
    return subprocess.call(cmd)


def main() -> int:
    seed_db()
    proc = start_server()
    try:
        if not wait_for_ready(30):
            proc.terminate()
            proc.wait(timeout=5)
            return 2

        rc_probe = run_login_probe()
        if rc_probe != 0:
            print("login_probe did not find a running server or login failed")

        rc_smoke = run_prod_smoke()
        print("Smoke test exit code:", rc_smoke)
        return rc_smoke
    finally:
        print("Shutting down server...")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()


if __name__ == "__main__":
    raise SystemExit(main())
