"""
Klerno Labs - Safe Console Output Utility
Fixes UnicodeEncodeError by providing safe console output that handles all characters.
"""

import builtins
import codecs
import contextlib
import os
import sys


class SafeConsole:
    """
    Safe console output that handles Unicode characters properly on all platforms.
    Prevents UnicodeEncodeError: 'charmap' codec can't encode character errors.
    """

    def __init__(self):
        self._setup_unicode_console()

    def _setup_unicode_console(self):
        """Setup console to handle Unicode properly."""
        # For Windows, ensure UTF-8 encoding
        if sys.platform.startswith("win"):
            # Try to set console code page to UTF-8
            with contextlib.suppress(builtins.BaseException):
                os.system("chcp 65001 > nul")

            # Reconfigure stdout/stderr for UTF-8
            try:
                if hasattr(sys.stdout, "reconfigure"):
                    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
                    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
                else:
                    # Fallback for older Python versions
                    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "replace")
                    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "replace")
            except Exception:
                # If reconfiguration fails, we'll use safe_print method
                pass

    def safe_print(self, *args, **kwargs):
        """
        Print function that safely handles Unicode characters.

        Args:
            *args: Arguments to print
            **kwargs: Keyword arguments for print function
        """
        try:
            print(*args, **kwargs)
        except UnicodeEncodeError:
            # Convert problematic Unicode characters to safe alternatives
            safe_args = []
            for arg in args:
                if isinstance(arg, str):
                    # Replace problematic Unicode characters
                    safe_arg = (
                        arg.replace("✅", "[OK]")
                        .replace("❌", "[ERROR]")
                        .replace("⚠️", "[WARNING]")
                        .replace("🔧", "[TOOL]")
                        .replace("📊", "[DATA]")
                        .replace("🚀", "[LAUNCH]")
                        .replace("💾", "[SAVE]")
                        .replace("🔍", "[SEARCH]")
                        .replace("📝", "[NOTE]")
                        .replace("⭐", "[STAR]")
                    )

                    # Encode to ASCII with replacement for any remaining issues
                    safe_arg = safe_arg.encode("ascii", errors="replace").decode(
                        "ascii"
                    )
                    safe_args.append(safe_arg)
                else:
                    safe_args.append(str(arg))

            print(*safe_args, **kwargs)

    def format_status(self, status: str, message: str) -> str:
        """
        Format a status message with safe Unicode alternatives.

        Args:
            status: Status type ('success', 'error', 'warning', 'info')
            message: Status message

        Returns:
            str: Safely formatted status message
        """
        status_symbols = {
            "success": "[OK]",
            "error": "[ERROR]",
            "warning": "[WARNING]",
            "info": "[INFO]",
        }

        symbol = status_symbols.get(status.lower(), "[INFO]")
        return f"{symbol} {message}"


# Global safe console instance
safe_console = SafeConsole()


# Convenience functions
def safe_print(*args, **kwargs):
    """Safe print function that handles Unicode errors."""
    safe_console.safe_print(*args, **kwargs)


def print_success(message: str):
    """Print a success message safely."""
    safe_console.safe_print(safe_console.format_status("success", message))


def print_error(message: str):
    """Print an error message safely."""
    safe_console.safe_print(safe_console.format_status("error", message))


def print_warning(message: str):
    """Print a warning message safely."""
    safe_console.safe_print(safe_console.format_status("warning", message))


def print_info(message: str):
    """Print an info message safely."""
    safe_console.safe_print(safe_console.format_status("info", message))
