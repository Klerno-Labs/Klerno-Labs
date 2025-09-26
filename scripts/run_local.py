"""Run the app locally with safe defaults.

This script sets a few development environment variables and launches Uvicorn
so you don't need to change PowerShell execution policies to run the app.
"""

import os
import socket
import sys
from pathlib import Path

# Only apply dev-friendly defaults when not running tests. Tests often
# rely on specific env var absence/values and should control APP_ENV
# themselves. If APP_ENV=="test" we avoid mutating the environment.
if os.getenv("APP_ENV", "") != "test":
    # Dev-friendly defaults (only set if not already present)
    os.environ.setdefault("APP_ENV", "development")
    os.environ.setdefault("X_API_KEY", "dev-local-api-key")
    os.environ.setdefault("API_KEY", "dev-local-api-key")
    os.environ.setdefault("JWT_SECRET", "dev-secret-change-me")
    os.environ.setdefault("DATABASE_URL", "sqlite:///./data/klerno.db")


# Ensure data dir exists
Path("data").mkdir(parents=True, exist_ok=True)


def main() -> None:
    import uvicorn

    # Ensure the project root is on sys.path so `import app` works even when
    # the process has a different working directory (this can happen when
    # started from external shells or background processes).
    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    print(f"[run_local] project_root={project_root}")

    # Allow overriding the local port via env var for convenience
    port = int(os.getenv("LOCAL_PORT", "8000"))
    host = "127.0.0.1"

    # If the requested port is occupied, prefer picking a free fallback port
    # automatically rather than failing outright. This keeps local dev fast
    # and avoids forcing contributors to hunt for PIDs on Windows.
    def _is_port_open(h: str, p: int) -> bool:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.5)
        try:
            s.connect((h, p))
        except Exception:
            return False
        finally:
            try:
                s.close()
            except Exception:
                pass
        return True

    if _is_port_open(host, port):
        print(f"[run_local] requested port {port} appears to be in use.")
        # Try to find a free ephemeral port (8001..8100) before giving up
        fallback = None
        for candidate in range(8001, 8101):
            if not _is_port_open(host, candidate):
                fallback = candidate
                break
        if fallback is None:
            print(
                "No free ports found in 8001-8100. Either stop the process using the port or set LOCAL_PORT to a free port manually."
            )
            print(
                "To inspect the owner on Windows: Get-NetTCPConnection -LocalPort {0} | Format-List *".format(
                    port
                )
            )
            sys.exit(1)
        print(
            f"[run_local] will start on fallback port {fallback} instead; to force 8000 stop the owning process or set LOCAL_PORT."
        )
        port = fallback

    # Import the FastAPI app object directly to avoid string-based import issues
    try:
        from app.main import app as fastapi_app
    except Exception as exc:
        # Provide a clearer error message before re-raising
        print(f"[run_local] import error: {exc!r}")
        raise

    # Disable reload here to avoid subprocess import path issues on Windows
    try:
        uvicorn.run(fastapi_app, host=host, port=port, reload=False)
    except OSError as exc:
        # Common case on Windows is errno 10048 when the port is in use.
        if getattr(exc, "errno", None) in (10048, 98):
            print(f"[run_local] OSError while binding to {host}:{port}: {exc}")
            print(
                "The port is already in use. Use the PowerShell commands printed earlier to find and stop the owning process."
            )
            sys.exit(1)
        raise


if __name__ == "__main__":
    main()
