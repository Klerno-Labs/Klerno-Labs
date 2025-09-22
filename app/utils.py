"""Small utility helpers used by tests.

This is intentionally minimal: implement the few functions tests import.
"""
import re
from decimal import Decimal


def get_exchange_rate(from_currency: str, to_currency: str) -> float:
    """Stub: in tests this is patched, so return 1.0 by default."""
    return 1.0


def convert_currency(
    amount: float | int | Decimal,
    from_currency: str,
    to_currency: str,
) -> float:
    """Convert using a deterministic stubbed exchange rate.

    Tests may patch get_exchange_rate to provide different rates.
    """
    rate = get_exchange_rate(from_currency, to_currency)
    return float(Decimal(str(amount)) * Decimal(str(rate)))


def validate_email(email: str) -> bool:
    # simple regex for tests
    return re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email) is not None


def validate_amount(amount: int | float | Decimal) -> bool:
    try:
        return float(amount) >= 0
    except Exception:
        return False


__all__ = ["convert_currency", "validate_email", "validate_amount"]


def to_mapping(obj: object) -> dict:
    """Safely convert mapping-like or row-like objects into a plain dict.

    Returns an empty dict on failure. This helper centralizes defensive
    logic so callers can avoid repeated hasattr(..., 'keys') checks.
    """
    from collections.abc import Mapping
    from typing import Any, cast

    if isinstance(obj, Mapping):
        return dict(obj)
    keys = getattr(obj, "keys", None)
    if callable(keys):
        try:
            # keys() may return a dict_keys or other iterable; cast to Any
            ks = list(cast(Any, keys()))
            any_obj = cast(Any, obj)
            return {k: any_obj[k] for k in ks}
        except Exception:
            return {}

    return {}


__all__.append("to_mapping")
