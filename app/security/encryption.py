"""Minimal encryption shim used by unit tests.

This is NOT production-grade encryption. It's only intended to satisfy
test imports and round-trip behavior (encrypt -> decrypt) during unit
tests. For real apps use a proper KMS or cryptography library.
"""

import base64
import json
from typing import Any


def encrypt_data(data: Any) -> str:
    """Encode input to a base64 string. Accepts str or JSON-serializable data."""
    if isinstance(data, str):
        raw = data.encode("utf-8")
    else:
        raw = json.dumps(data).encode("utf-8")
    return base64.b64encode(raw).decode("utf-8")


def decrypt_data(encoded: str) -> Any:
    """Decode base64 string. Attempt to return a str, otherwise raw bytes."""
    raw = base64.b64decode(encoded.encode("utf-8"))
    try:
        return raw.decode("utf-8")
    except Exception:
        return raw


__all__ = ["encrypt_data", "decrypt_data"]
