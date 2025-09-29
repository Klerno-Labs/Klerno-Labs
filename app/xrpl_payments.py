"""Lightweight compatibility layer for XRPL payment helpers.

This module provides minimal, deterministic implementations of the functions
used by `app.paywall` and tests. It's intentionally small and does not
contact any external XRPL services. Replace with a real implementation when
you reintroduce XRPL support.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any


def create_payment_request(*args, **kwargs) -> dict[str, Any]:
    """Create a simple payment request dictionary.

    Accepts either the old keyword args (amount, recipient, sender, memo)
    or the newer-style (user_id, amount_xrp, description). Returns a dict
    with both `id` and `request_id` for backwards compatibility.
    """
    now = datetime.now(UTC)
    payment_id = str(uuid.uuid4())

    # normalize parameters
    amount = kwargs.get("amount_xrp") or kwargs.get("amount") or 0.0
    destination = kwargs.get("recipient") or kwargs.get("destination") or ""

    return {
        "id": payment_id,
        "request_id": payment_id,
        "destination": destination,
        "recipient": destination,
        "amount_xrp": amount,
        "destination_tag": kwargs.get("destination_tag", "12345"),
        "created_at": now.isoformat(),
        "expires_at": (now + timedelta(days=1)).isoformat(),
        "status": "pending",
    }


def verify_payment(payment_request_or_id: Any, tx_hash: str | None = None) -> Any:
    """Verify a payment.

    This function supports two calling conventions used in the codebase:
    - verify_payment(payment_request: dict, tx_hash) -> (bool, message, details)
    - verify_payment(request_id: str, tx_hash) -> dict with keys 'verified' etc.

    The default behavior is a no-op non-verified response. Tests or calling
    code can mock this function where a verified result is required.
    """
    # If passed a dict-like payment request, return a tuple as older callers
    # expect (bool, message, details).
    if isinstance(payment_request_or_id, dict):
        return False, "No matching payment found", None

    # Otherwise, caller passed an id; return a dict-shaped result used by
    # some endpoints.
    return {
        "verified": False,
        "transaction": {},
        "error": "verification not performed",
    }


def get_network_info() -> dict[str, Any]:
    """Return a minimal network info dict used by admin endpoints/tests."""
    return {
        "network": "testnet",
        "connected": False,
        "destination_wallet": "",
        "subscription_price_xrp": 0.0,
        "subscription_duration_days": 0,
    }
