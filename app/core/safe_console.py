"""Minimal safe console utility for Klerno Labs.

This module provides tiny, well-typed helpers that avoid raising
UnicodeEncodeError on environments with limited console encodings. The
implementation is intentionally small to simplify static analysis and keep the
runtime behavior predictable.
"""

from typing import Any


def safe_print(*args, **kwargs: Any) -> None:
    """Print arguments but fall back to ASCII-safe output on encoding errors.

    All non-str arguments are stringified with str(). Strings are encoded to
    ASCII with replacement on UnicodeEncodeError to ensure the print call
    always succeeds.
    """
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        safe_args: list[str] = []
        for arg in args:
            if isinstance(arg, str):
                safe_args.append(arg.encode("ascii", errors="replace").decode("ascii"))
            else:
                safe_args.append(str(arg))

        print(*safe_args, **kwargs)


def format_status(status: str, message: str) -> str:
    """Return a one-line status message with a safe prefix."""
    status_symbols = {
        "success": "[OK]",
        "error": "[ERROR]",
        "warning": "[WARNING]",
        "info": "[INFO]",
    }
    return f"{status_symbols.get(status.lower(), '[INFO]')} {message}"
