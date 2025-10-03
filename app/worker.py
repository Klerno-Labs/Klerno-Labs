
"""Removed worker helpers.

This module was empty previously. Keep a no-op shim to avoid import-time errors
in modules that still reference `app.worker` during consolidation.
"""


def noop() -> None:
    """No-op placeholder for removed worker functionality."""
    return None
