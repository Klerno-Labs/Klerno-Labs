import os
import sys

print("python:", sys.executable)
print("cwd:", os.getcwd())
print("\nsys.path[0]:", sys.path[0])
print("\nTop-level repo files/folders that start with pandas:")
for name in sorted(os.listdir(sys.path[0] or ".")):
    if name.lower().startswith("pandas"):
        print(" -", name)

print("\nChecking sys.modules for entries starting with pandas:")
found = False
for k in sorted([k for k in sys.modules.keys() if k.startswith("pandas")]):
    found = True
    mod = sys.modules[k]
    print(" -", k, "->", getattr(mod, "__file__", repr(mod)))
if not found:
    print(" - none")

print("\nAttempting to import pandas now:")
try:
    import importlib

    pandas = importlib.import_module("pandas")
    print("Imported pandas from:", getattr(pandas, "__file__", None))
    print("pandas.__package__:", getattr(pandas, "__package__", None))
except Exception:
    import traceback

    print("Import failed:")
    traceback.print_exc()
