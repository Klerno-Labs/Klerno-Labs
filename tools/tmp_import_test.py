import importlib
import sys
import traceback

sys.path.insert(0, ".")
try:
    m = importlib.import_module("enterprise_main_v2")
except Exception:
    traceback.print_exc()
