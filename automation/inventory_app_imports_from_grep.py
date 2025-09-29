"""Produce a compact inventory JSON using repository grep results.

This script is intended to run quickly and avoid scanning large OneDrive
trees. It reads a small set of search matches embedded here and writes
`automation/inventory_app_imports.json` with module -> ref_count and
examples.
"""

import json
from pathlib import Path

ROOT = Path(r"c:\Users\chatf\OneDrive\Desktop\Klerno Labs")
OUT = ROOT / "automation" / "inventory_app_imports.json"

# Minimal, manually curated reference map derived from fast grep runs.
# Each key is a module filename (without .py). The values are a list of
# relative file paths that reference the module. This is a pragmatic
# snapshot for the initial consolidation pass.
REFS = {
    "main": [
        "tests/test_iso_endpoints.py",
        "tests/test_api.py",
        "tests/conftest.py",
    ],
    "models": [
        "tests/test_models.py",
        "integrations/bsc.py",
        "integrations/xrp.py",
    ],
    "guardian": [
        "tests/test_guardian.py",
        "guardian.py",
    ],
    "compliance": [
        "tests/test_compliance.py",
        "tests/test_unit_comprehensive.py",
    ],
    "iso20022_compliance": [
        "tests/test_iso20022.py",
        "tests/test_iso_parsers.py",
    ],
    "settings": [
        "tests/test_integration.py",
        "enterprise_main_v2.py",
    ],
    "logging_config": [
        "tests/test_integration.py",
        "app/middleware.py",
    ],
    "exceptions": [
        "tests/test_integration.py",
        "app/middleware.py",
    ],
    # many more modules exist; modules with no entry here will be treated as
    # zero-refs for now (candidates for deeper analysis)
}

(ROOT / "automation").mkdir(parents=True, exist_ok=True)

out = []
app_dir = ROOT / "app"
for fn in sorted(p.name for p in app_dir.iterdir() if p.is_file()):
    if not fn.endswith(".py"):
        continue
    mod = fn[:-3]
    refs = REFS.get(mod, [])
    out.append(
        {
            "module": mod,
            "refs": len(refs),
            "examples": ";".join(refs[:5]),
        }
    )

with OUT.open("w", encoding="utf-8") as fh:
    json.dump(out, fh, indent=2)

print("Wrote", OUT)
