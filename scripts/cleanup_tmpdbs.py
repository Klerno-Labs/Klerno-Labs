#!/usr/bin/env python3
"""Remove repository tmp_*.db files before tests run.

This script is intentionally small and low-risk: it only removes files that
match the pattern "tmp_*.db" under the repository root. It supports a
--recursive flag to scan subdirectories, and a --dry-run flag to print what
would be removed without deleting anything.

Usage examples:
  python scripts/cleanup_tmpdbs.py            # remove tmp_*.db in repo root
  python scripts/cleanup_tmpdbs.py --recursive
  python scripts/cleanup_tmpdbs.py --dry-run

This file is added to the branch so CI jobs that run the cleanup step can
reliably find and execute the script from the checked-out merge ref.
"""

from __future__ import annotations

import argparse
import fnmatch
import os
from pathlib import Path
from typing import Iterator


def find_tmp_db_files(root: Path, recursive: bool = False) -> Iterator[Path]:
    pattern = "tmp_*.db"
    if recursive:
        for dirpath, dirnames, filenames in os.walk(root):
            # skip virtualenvs and .git
            dirnames[:] = [
                d for d in dirnames if d not in (".git", ".venv", "venv", "env")
            ]
            for fname in fnmatch.filter(filenames, pattern):
                yield Path(dirpath) / fname
    else:
        for p in root.iterdir():
            if p.is_file() and fnmatch.fnmatch(p.name, pattern):
                yield p


def main() -> int:
    parser = argparse.ArgumentParser(description="Remove tmp_*.db files in the repo")
    parser.add_argument(
        "--recursive", "-r", action="store_true", help="scan subdirectories"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="list files that would be removed"
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="repository root (defaults to CWD)",
    )
    args = parser.parse_args()

    root = args.root.resolve()
    removed = 0
    candidates = list(find_tmp_db_files(root, recursive=args.recursive))

    if not candidates:
        print("No tmp_*.db files found.")
        return 0

    for p in candidates:
        try:
            if args.dry_run:
                print(f"DRY-RUN would remove: {p}")
            else:
                print(f"Removing: {p}")
                p.unlink()
                removed += 1
        except Exception as exc:  # pragma: no cover - extremely defensive in CI helper
            print(f"Failed to remove {p}: {exc}")

    if args.dry_run:
        print(f"Found {len(candidates)} tmp_*.db file(s) (dry-run).")
        return 0

    print(f"Removed {removed} tmp_*.db file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
"""
Cross-platform cleanup script to remove temporary SQLite DB files in the
repository root matching the pattern `tmp_*.db`.

Usage:
  python scripts/cleanup_tmpdbs.py [--recursive]

By default this removes files only in the repository root (safe-by-default).
With --recursive it will search subdirectories too.
"""

from __future__ import annotations

import argparse
import fnmatch
import os
from pathlib import Path
from typing import Iterable


def find_tmp_dbs(root: Path, recursive: bool = False) -> Iterable[Path]:
    pattern = "tmp_*.db"
    if not recursive:
        for p in root.iterdir():
            if p.is_file() and fnmatch.fnmatch(p.name, pattern):
                yield p
    else:
        for p in root.rglob(pattern):
            if p.is_file():
                yield p


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--recursive", action="store_true", help="Search subdirs recursively"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Print files that would be removed"
    )
    args = parser.parse_args()

    # Determine repository root (assume scripts directory lives in repo root)
    script_path = Path(__file__).resolve()
    repo_root = script_path.parents[1]

    removed = 0
    for p in find_tmp_dbs(repo_root, recursive=args.recursive):
        try:
            if args.dry_run:
                print(f"Would remove: {p}")
            else:
                print(f"Removing: {p}")
                p.unlink()
            removed += 1
        except Exception as exc:  # pragma: no cover - simple best-effort cleanup
            print(f"Failed to remove {p}: {exc}")

    print(f"Done. {removed} file(s) processed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
