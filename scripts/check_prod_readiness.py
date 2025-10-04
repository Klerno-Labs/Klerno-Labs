"""Lightweight production readiness checks used by CI and local dev.

This file intentionally keeps checks simple and side-effect free so CI can
import and run it quickly. The checks are conservative: they warn in
non-production to preserve developer experience and fail in production
when a critical setting is missing or insecure.
"""

from __future__ import annotations

import json
import os
import socket
import sys
from pathlib import Path

WEAK_SECRETS = {"changeme", "secret", "dev", "your-secret-key-change-in-production"}


def warn(msg: str) -> None:
    print(f"[WARN] {msg}")


def fail(msg: str) -> None:
    print(f"[FAIL] {msg}")


def ok(msg: str) -> None:
    print(f"[OK] {msg}")


def _env_bool(name: str) -> bool:
    return os.environ.get(name, "").lower() in ("1", "true", "yes", "on")


def check_env_vars() -> bool:
    """Return True when environment is acceptable (warnings ok), False on hard failures."""
    if os.environ.get("APP_ENV") == "production":
        if not os.getenv("JWT_SECRET"):
            fail("Missing required env var: JWT_SECRET")
            return False
    else:
        warn("Not running in production mode; some checks are relaxed")
    return True


def check_secret_strength() -> bool:
    secret = os.getenv("JWT_SECRET", "")
    if os.environ.get("APP_ENV") != "production" and not secret:
        warn("JWT_SECRET not set (non-production).")
        return True
    if not secret:
        fail("JWT_SECRET not set")
        return False
    if len(secret) < 16 or secret.lower() in WEAK_SECRETS:
        fail("JWT_SECRET weak or default; must be rotated for production")
        return False
    ok("JWT_SECRET strength OK")
    return True


def check_database_url() -> bool:
    url = os.getenv("DATABASE_URL", "")
    if not url:
        warn("DATABASE_URL not set (SQLite fallback). Use PostgreSQL in production.")
        return True
    if url.startswith("sqlite:"):
        warn("SQLite in use. Migrate to PostgreSQL for production workloads.")
        return True
    ok("DATABASE_URL present and appears non-sqlite")
    return True


def check_bind_port() -> None:
    port = int(os.getenv("PORT", "8000"))
    if port < 1024:
        warn(
            f"PORT {port} is a privileged port; prefer >=1024 in container unless root.",
        )
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) == 0:
                warn(
                    f"Port {port} appears in use locally; ensure unique port per instance.",
                )
    except Exception:
        # Non-fatal; some CI/persistent environments restrict socket ops
        warn("Unable to probe local port binding; skipping port check")


def check_files() -> None:
    suspicious = [".env", "data/api_key.secret"]
    for f in suspicious:
        if Path(f).exists():
            warn(f"Sensitive file present in repo root: {f}")
    ok("Checked for common sensitive files")


def check_import_app() -> bool:
    """Attempt to import the application package to surface import-time errors."""
    try:
        try:
            # common FastAPI entrypoint names that projects use
            import importlib

            for candidate in ("enterprise_main_v2", "main", "app", "preview_server"):
                try:
                    importlib.import_module(candidate)
                    break
                except Exception:
                    continue
            else:
                # fallback to package import
                importlib.import_module("app")
        except Exception:
            # Reraise to outer handler
            raise
    except Exception as exc:  # pragma: no cover - environment dependent
        fail(f"Importing FastAPI app failed: {exc!r}")
        return False
    ok("Imported FastAPI app successfully")
    return True


def run_checks() -> list[str]:
    problems: list[str] = []
    if not check_env_vars():
        problems.append("Missing required environment variables for production")
    if not check_secret_strength():
        problems.append("Secret strength check failed")
    if not check_database_url():
        problems.append("Database configuration check failed")
    check_bind_port()
    check_files()
    if not check_import_app():
        problems.append("App import failed")
    return problems


def main() -> int:
    print("Running production readiness checks...\n")
    problems = run_checks()
    summary = {"ok": len(problems) == 0, "problems": problems}
    sys.stdout.write(json.dumps(summary, indent=2))
    sys.stdout.write("\n")
    return 0 if not problems else 2


if __name__ == "__main__":
    raise SystemExit(main())
