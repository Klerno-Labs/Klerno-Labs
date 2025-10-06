from __future__ import annotations

import base64
import json
import os
import time

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

# Precompute env & guard: require a non-expired JWT-like token for this optional test
_url = os.getenv("VITE_NEON_DATA_API_URL")
_token = os.getenv("NEON_API_KEY")
_is_jwt = bool(_token and _token.count(".") == 2)


def _jwt_expired(tok: str) -> bool:
    try:
        parts = tok.split(".")
        payload_b64 = parts[1]
        # base64url decode with padding
        padding = "=" * (-len(payload_b64) % 4)
        payload_json = base64.urlsafe_b64decode(payload_b64 + padding).decode()
        claims = json.loads(payload_json)
        exp = claims.get("exp")
        if not isinstance(exp, (int, float)):
            return False
        return exp <= time.time()
    except Exception:
        return False


_expired = bool(_is_jwt and _jwt_expired(_token or ""))
_should_run = bool(_url and _token and _is_jwt and not _expired)
_skip_reason = (
    "Neon Data API env variables not set"
    if not (_url and _token)
    else (
        "NEON_API_KEY is not a JWT (expected Neon Auth access token)"
        if not _is_jwt
        else "NEON_API_KEY JWT is expired"
    )
)


@pytest.mark.integration
@pytest.mark.skipif(not _should_run, reason=_skip_reason)
def test_neon_notes_happy_path_when_configured():
    r = client.get("/api/neon/notes")
    # With valid env + token this should be authorized and return JSON array or object
    if r.status_code not in (200, 206):
        # Provide a compact hint to help diagnose common misconfigurations
        detail = None
        try:
            detail = r.json()
        except Exception:
            detail = r.text
        pytest.fail(
            f"Neon /notes expected 200/206, got {r.status_code}. Body: {detail}"
        )
    data = r.json()
    assert isinstance(data, (list, dict))
