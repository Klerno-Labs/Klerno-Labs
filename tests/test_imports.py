import importlib
import sys


def test_analytics_imports_without_pandas():
    """Import app.analytics and ensure pandas isn't imported at module import time."""
    # remove pandas if present
    sys.modules.pop("pandas", None)
    # import the module
    mod = importlib.import_module("app.analytics")
    # pandas should not be in sys.modules after import unless the module required it
    assert (
        "pandas" not in sys.modules
        or getattr(mod, "_requires_pandas_at_import", False) is True
    )


def test_enterprise_analytics_imports_without_pandas():
    sys.modules.pop("pandas", None)
    mod = importlib.import_module("enterprise_analytics")
    assert (
        "pandas" not in sys.modules
        or getattr(mod, "_requires_pandas_at_import", False) is True
    )
