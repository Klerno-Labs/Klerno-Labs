import contextlib
import socket
import subprocess
import sys
import time
from contextlib import closing

import httpx

HOST = "127.0.0.1"
PORT = 8010
BASE_URL = f"http://{HOST}:{PORT}"
PATHS = ["/", "/health", "/docs", "/api/neon/notes"]


def wait_for_port(host: str, port: int, timeout: float = 15.0) -> bool:
    start = time.time()
    while time.time() - start < timeout:
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
            sock.settimeout(0.5)
            try:
                if sock.connect_ex((host, port)) == 0:
                    return True
            except OSError:
                pass
        time.sleep(0.2)
    return False


def main() -> int:
    # Start uvicorn server in a subprocess
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        HOST,
        "--port",
        str(PORT),
    ]
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    try:
        if not wait_for_port(HOST, PORT, timeout=20):
            print("Server failed to start within timeout.")
            with contextlib.suppress(Exception):
                proc.terminate()
            return 1

        ok = True
        with httpx.Client(timeout=10) as client:
            for p in PATHS:
                url = f"{BASE_URL}{p}"
                code: str | int
                try:
                    r = client.get(url)
                    code = r.status_code
                except Exception as e:
                    code = f"unreachable: {type(e).__name__}"
                print(f"  {p} -> {code}")
                if code == 404 or (
                    isinstance(code, str) and code.startswith("unreachable")
                ):
                    ok = False

        if not ok:
            print("Smoke test failed due to 404 or unreachable endpoints.")
            return 1
        print("Smoke test passed: no 404/unreachable.")
        return 0
    finally:
        try:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except Exception:
                proc.kill()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
