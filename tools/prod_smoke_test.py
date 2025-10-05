"""Production/staging smoke tests.

This script is intended to run against a deployed staging or pre-release
environment. It performs a few basic checks:
- GET {url}/ready (200)
- GET {url}/metrics (200 & contains Prometheus metrics)
- GET {url}/auth/me (200 when provided with token)

Usage:
    python tools/prod_smoke_test.py --url https://staging.example.com --token-file .run/dev_tokens.json

The script exits with code 0 if all checks pass, non-zero otherwise.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import httpx


def load_token(token_file: str) -> str | None:
    try:
        p = Path(token_file)
        with p.open(encoding="utf-8") as f:
            j = json.load(f)
            return j.get("tokens", {}).get("access_token")
    except Exception:
        return None


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--url",
        required=True,
        help="Base URL of the deployment (https://...)",
    )
    p.add_argument(
        "--token-file",
        help="Optional token JSON file (saved by login_probe)",
    )
    args = p.parse_args()

    url = args.url.rstrip("/")
    token = None
    if args.token_file:
        token = load_token(args.token_file)

    client = httpx.Client(timeout=10.0)

    checks = []

    # /ready
    try:
        r = client.get(f"{url}/ready")
        checks.append(("ready", r.status_code == 200, r.text[:200]))
    except Exception:
        return 2

    # /metrics
    try:
        r = client.get(f"{url}/metrics")
        ok = r.status_code == 200 and "# HELP" in r.text
        checks.append(("metrics", ok, r.text[:200]))
    except Exception:
        return 3

    # /auth/me (if token available)
    if token:
        try:
            headers = {"Authorization": f"Bearer {token}"}
            r = client.get(f"{url}/auth/me", headers=headers)
            checks.append(("auth.me", r.status_code == 200, r.text[:200]))
        except Exception:
            return 4

    ok_all = all(ok for _, ok, _ in checks)
    for _name, ok, _sample in checks:
        pass

    return 0 if ok_all else 5


if __name__ == "__main__":
    raise SystemExit(main())
