"""Inspect FastAPI routes and report duplicates.

Run:
  python -m scripts.inspect_routes
"""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path


def main() -> int:
    # Ensure project root on path
    here = Path(__file__).resolve()
    root = here.parent.parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    try:
        from app.main import app  # type: ignore
    except Exception as e:
        print(f"[FAIL] Unable to import app.main: {e!r}")
        return 2

    # Collect routes
    routes = []
    for r in app.router.routes:  # type: ignore[attr-defined]
        try:
            path = getattr(r, "path", None) or getattr(r, "path_format", None)
            methods = sorted(getattr(r, "methods", []) or [])
            name = getattr(r, "name", "")
            endpoint = getattr(r, "endpoint", None)
            endpoint_qual = None
            if endpoint is not None:
                mod = getattr(endpoint, "__module__", "")
                fn = getattr(endpoint, "__name__", repr(endpoint))
                endpoint_qual = f"{mod}:{fn}"
            routes.append((tuple(methods), path, name, endpoint_qual))
        except Exception:
            continue

    # Print all routes
    print("[ROUTES]")
    for methods, path, name, qual in sorted(routes, key=lambda x: (x[1] or "", x[0])):
        m = ",".join(methods) if methods else ""
        print(f"{m:<12} {path:<35} {name:<30} {qual or ''}")

    # Detect duplicates (method,path)
    buckets: dict[tuple[str, str], list[str]] = defaultdict(list)
    for methods, path, _name, qual in routes:
        if not path or not methods:
            continue
        for m in methods:
            buckets[(m, path)].append(qual or "<unknown>")

    dups = {k: v for k, v in buckets.items() if len(v) > 1}
    if dups:
        print("\n[DUPLICATES]")
        for (method, path), handlers in sorted(dups.items()):
            print(f"{method} {path} -> {len(handlers)} handlers:")
            for h in handlers:
                print(f"  - {h}")
        return 1

    print("\n[OK] No duplicate method+path routes detected")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
