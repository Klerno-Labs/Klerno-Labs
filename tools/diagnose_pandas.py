import sys
import traceback
from pathlib import Path

for p in sys.path:
    pass

root = Path(sys.path[0] or ".")
for p in root.iterdir():
    if p.name.lower().startswith("pandas"):
        pass

try:
    pass

except Exception:
    traceback.print_exc()

for _k in sorted([k for k in sys.modules if k.startswith("pandas")]):
    pass
