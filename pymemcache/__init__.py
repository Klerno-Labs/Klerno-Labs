"""Local shim package for pymemcache - only for type checking in this repo.

This package provides minimal .pyi-style runtime-free typing helpers so mypy
doesn't require installing external stubs during CI or local runs.
"""

__all__ = ["client"]
