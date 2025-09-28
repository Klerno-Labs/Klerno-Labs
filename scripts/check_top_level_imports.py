"""Simple script to scan Python files for top-level imports of heavy packages.

Exits non-zero if any top-level imports of pandas/tensorflow/sklearn are found.
"""

import ast
import sys
from pathlib import Path

HEAVY = {"pandas", "tensorflow", "sklearn"}


def is_top_level_import(node):
    return isinstance(node, (ast.Import, ast.ImportFrom))


def scan_file(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        src = path.read_text(encoding="utf8")
    except Exception:
        return errors
    try:
        tree = ast.parse(src)
    except Exception:
        return errors

    for node in tree.body:
        if is_top_level_import(node):
            if isinstance(node, ast.Import):
                for n in node.names:
                    name = n.name.split(".")[0]
                    if name in HEAVY:
                        errors.append(f"{path}: top-level import {name}")
            elif isinstance(node, ast.ImportFrom) and node.module:
                name = node.module.split(".")[0]
                if name in HEAVY:
                    errors.append(f"{path}: top-level from import {name}")
    return errors


def main():
    repo = Path(__file__).resolve().parents[1]
    py_files = list(repo.rglob("*.py"))
    errs: list[str] = []
    for p in py_files:
        # ignore virtualenv, __pycache__, and third-party dirs
        if "site-packages" in str(p) or "__pycache__" in str(p):
            continue
        errs.extend(scan_file(p))

    if errs:
        print("Top-level heavy imports found:")
        for e in errs:
            print(" -", e)
        sys.exit(2)


if __name__ == "__main__":
    main()
