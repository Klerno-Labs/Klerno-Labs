"""Make `scripts` a package so imports like `from scripts import init_db_if_needed` work
and static tools (mypy) do not report the same file under multiple module names.

This is intentionally minimal.
"""

__all__ = []
