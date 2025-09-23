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
    print("Failed to import project modules:", e)
    raise SystemExit(1)


def main():
    email = os.getenv("DEV_ADMIN_EMAIL", "klerno@outlook.com").strip()
    password = os.getenv("DEV_ADMIN_PASSWORD", "Labs2025")

    try:
        store.init_db()
    except Exception as e:
        print("Warning: init_db() failed (continuing):", e)

    existing = store.get_user_by_email(email)
    if existing:
        if isinstance(existing, dict):
            ex_email = existing.get("email")
            ex_role = existing.get("role")
        else:
            ex_email = existing
            ex_role = "unknown"

        print(f"Admin user already exists: {ex_email} (role={ex_role})")
        return

    pw_hash = hash_pw(password)
    try:
        user = store.create_user(email=email, password_hash=pw_hash, role="admin", subscription_active=True)
        # store.create_user may return dict-like or a model; handle both safely
        if isinstance(user, dict):
            uid = user.get('id')
            uemail = user.get('email')
        else:
            uid = getattr(user, 'id', None)
            uemail = getattr(user, 'email', None)
        print(f"Created admin user: {uemail} (id={uid})")
        print("You can now start the app and sign in with these credentials.")
    except Exception as e:
        print("Failed to create admin user:", e)
        raise SystemExit(2)


if __name__ == '__main__':
    main()
