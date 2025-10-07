"""
Neon Data API diagnostic helper.

What it does:
- Reads VITE_NEON_DATA_API_URL and NEON_API_KEY from env
- Validates the token looks like a JWT and prints decoded header/payload (no signature verification)
- Performs two HTTP calls:
  1) GET <base>/ (root) – many PostgREST return 404/400; we only care about auth/error text
  2) GET <base>/notes?select=*&limit=1 – prints status and compact body

Usage:
  set VITE_NEON_DATA_API_URL and NEON_API_KEY in your shell, then:
    python scripts/neon_diag.py

Notes:
- This tool is read-only and prints at most the first ~2 KB of any response bodies.
- It helps distinguish between: invalid token vs missing table vs RLS/role errors.
"""

from __future__ import annotations

import base64
import json
import os
import sys
from textwrap import shorten

import httpx


def b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def decode_jwt(token: str) -> tuple[dict, dict] | None:
    try:
        header_b64, payload_b64, _sig = token.split(".", 2)
        header = json.loads(b64url_decode(header_b64))
        payload = json.loads(b64url_decode(payload_b64))
        return header, payload
    except Exception:
        return None


def main() -> int:
    base = os.getenv("VITE_NEON_DATA_API_URL") or os.getenv("NEON_DATA_API_URL")
    token = os.getenv("NEON_API_KEY")

    if not base:
        print("ERROR: VITE_NEON_DATA_API_URL (or NEON_DATA_API_URL) is not set.")
        return 2
    if not token:
        print(
            "ERROR: NEON_API_KEY is not set. This must be a Neon Auth ACCESS TOKEN (JWT), not a management API key."
        )
        return 2

    print(f"Base URL: {base}")
    print(f"Token looks like JWT: {'yes' if token.count('.') == 2 else 'no'}")

    decoded = decode_jwt(token)
    if decoded is None:
        print(
            "WARN: Token could not be decoded as JWT; Neon Data API expects a Bearer JWT from Neon Auth."
        )
    else:
        header, payload = decoded
        # Print a compact view of key claims
        claims = {
            k: payload.get(k)
            for k in ("iss", "aud", "sub", "role", "exp", "iat")
            if k in payload
        }
        print("JWT header:", json.dumps(header, indent=2))
        print("JWT claims:", json.dumps(claims, indent=2))

    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}

    def show(resp: httpx.Response, label: str) -> None:
        body = resp.text
        compact = shorten(body.replace("\n", " "), width=2000, placeholder=" …")
        print(f"\n[{label}] {resp.request.method} {resp.request.url}")
        print(f"Status: {resp.status_code}")
        if resp.headers.get("content-type", "").startswith("application/json"):
            try:
                parsed = resp.json()
                compact = json.dumps(parsed, indent=2)[:2000]
            except Exception:
                pass
        print("Body:\n" + compact)

    try:
        with httpx.Client(timeout=20) as client:
            # 1) Root ping (may be 400/404/401 depending on Data API)
            r1 = client.get(base, headers=headers)
            show(r1, "root")

            # 2) Notes minimal query
            notes_url = base.rstrip("/") + "/notes?select=*&limit=1"
            r2 = client.get(notes_url, headers=headers)
            show(r2, "notes")

            # Quick hints
            if r2.status_code == 401:
                print(
                    "\nHint: 401 Unauthorized — token is missing/invalid/expired or not accepted by Neon Data API."
                )
            elif r2.status_code == 404:
                print(
                    "\nHint: 404 Not Found — 'notes' table may not exist in the target database/schema."
                )
            elif r2.status_code == 400:
                print(
                    "\nHint: 400 Bad Request — often indicates a JWT/claims mismatch (e.g., wrong token type), "
                    "or PostgREST error surfaced by RLS/policies/functions. Inspect body for details."
                )

    except httpx.RequestError as e:
        print(f"HTTP error: {e}")
        return 3

    return 0


if __name__ == "__main__":
    sys.exit(main())
