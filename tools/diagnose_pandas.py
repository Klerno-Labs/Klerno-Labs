import sys
import traceback

print("python:", sys.executable)
print("version:", sys.version)
print("cwd (sys.path[0]):", sys.path[0])
import os

# ruff: noqa: E402
import sys
import traceback

print("python:", sys.executable)
print("version:", sys.version)
print("cwd (sys.path[0]):", sys.path[0])
print("\nsys.path:")
for p in sys.path:
    print(" -", p)

print("\nLooking for local files named pandas* in repo root:")
for name in os.listdir(sys.path[0] or "."):
    if name.lower().startswith("pandas"):
        print(" *", name)

print("\nAttempting to import pandas...")
try:
    import pandas

    print("pandas module file:", getattr(pandas, "__file__", repr(pandas)))
    print("pandas package path:", getattr(pandas, "__path__", None))
except Exception:
    print("Import failed:")
    traceback.print_exc()

print("\nCurrently loaded sys.modules entries for pandas namespace:")
for k in sorted([k for k in sys.modules if k.startswith("pandas")]):
    print(" -", k, "->", getattr(sys.modules[k], "__file__", repr(sys.modules[k])))
    print("\nAttempting to import pandas...")
