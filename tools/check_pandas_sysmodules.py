import sys
from pathlib import Path

root = Path(sys.path[0] or ".")
for name in sorted([p.name for p in root.iterdir() if p.exists()]):
    if name.lower().startswith("pandas"):
        pass

found = False
for k in sorted([k for k in sys.modules if k.startswith("pandas")]):
    found = True
    mod = sys.modules[k]
if not found:
    pass

try:
    import importlib

    pandas = importlib.import_module("pandas")
except Exception:
    import traceback

    traceback.print_exc()
