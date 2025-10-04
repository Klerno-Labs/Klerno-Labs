"""Quick import checker for modified modules.

Run with the repo venv python to surface syntax/import errors.

Example:
    "./.venv-py311/Scripts/python.exe" tools/check_imports_tool.py

"""

import importlib
import json

modules = [
    "app.compliance_reporting",
    "app.multi_chain_support",
    "app.performance_optimization_advanced",
]

errs = []
importlib.invalidate_caches()
for m in modules:
    try:
        importlib.reload(importlib.import_module(m))
    except Exception as e:
        errs.append({"module": m, "error": str(e)})

print(json.dumps({"import_errors": errs}, indent=2))
