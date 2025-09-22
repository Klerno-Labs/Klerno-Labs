
"""Lightweight compatibility shim for xrpl_payments_mock.

This module used to contain a test/mock helper. It's now a minimal shim
to avoid import-time errors in places that may still import it.
If tests import this module directly, they'll still get a module object
but the shim intentionally performs no runtime network calls.
"""

import logging

logger = logging.getLogger(__name__)


def create_payment_request(*args, **kwargs):
    """Compatibility stub: return a deterministic dummy payment request."""
    logger.debug("xrpl_payments_mock.create_payment_request called (shim)")
    return {"id": "mock-payment", "address": "rMockAddress", "amount": 0}


def verify_payment(*args, **kwargs):
    """Compatibility stub: always return False (no payment)."""
    logger.debug("xrpl_payments_mock.verify_payment called (shim)")
    return False
