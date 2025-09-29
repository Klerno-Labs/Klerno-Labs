"""No-op shim for removed task helpers.

This file was empty. We keep a minimal shim to avoid import-time errors
in modules that may still `import app.tasks` during consolidation.
"""


def noop_task():
    """Placeholder function for task runner APIs."""
    return None
