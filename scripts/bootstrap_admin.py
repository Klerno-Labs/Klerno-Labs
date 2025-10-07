r"""Bootstrap a development admin user directly into the project's database.

This script is idempotent and safe for local development. It uses the
project's `app.store` helpers so it respects the same DB path and schema
as the application.

Usage (PowerShell):


Environment variables respected (optional):

    # activate venv then run the script
    . .\.venv-py311\Scripts\Activate.ps1
    .\.venv-py311\Scripts\python.exe scripts\bootstrap_admin.py

Environment variables respected (optional):
    DEV_ADMIN_EMAIL (default: klerno@outlook.com)
    DEV_ADMIN_PASSWORD (default: Labs2025)
"""

import contextlib
import os
import sys
from pathlib import Path

# Ensure project root is on sys.path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

try:
    from app import store
    from app.security_session import hash_pw
except Exception as e:
    raise SystemExit(1) from e


def main() -> None:
    email = os.getenv("DEV_ADMIN_EMAIL", "klerno@outlook.com").strip()
    password = os.getenv("DEV_ADMIN_PASSWORD", "Labs2025")

    with contextlib.suppress(Exception):
        store.init_db()

    existing = store.get_user_by_email(email)
    if existing:
        if isinstance(existing, dict):
            existing.get("email")
            existing.get("role")
        else:
            pass

        return

    pw_hash = hash_pw(password)
    try:
        user = store.create_user(
            email=email,
            password_hash=pw_hash,
            role="admin",
            subscription_active=True,
        )
        # store.create_user may return dict-like or a model; handle both safely
        if isinstance(user, dict):
            user.get("id")
            user.get("email")
        else:
            getattr(user, "id", None)
            getattr(user, "email", None)
    except Exception as e:
        raise SystemExit(2) from e


if __name__ == "__main__":
    main()
