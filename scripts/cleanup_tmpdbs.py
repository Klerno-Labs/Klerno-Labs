#!/usr/bin/env python3
"""Cross-platform cleanup script to remove temporary SQLite DB files.

This helper removes files matching the pattern `tmp_*.db` under the
repository root. It's intentionally conservative: by default it removes
files only in the repository root. Use --recursive to scan subdirectories.

Examples:
  python scripts/cleanup_tmpdbs.py
  python scripts/cleanup_tmpdbs.py --recursive
  python scripts/cleanup_tmpdbs.py --dry-run
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
        # Walk the tree but skip common virtualenv and git folders
        for dirpath, dirnames, filenames in os.walk(root):
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
        "--root", type=Path, help="repository root (defaults to repo parent of scripts)"
    )
    args = parser.parse_args()

    # Determine repo root: prefer explicit --root, else assume scripts/ is at repo_root/scripts
    if args.root:
        repo_root = args.root.resolve()
    else:
        repo_root = Path(__file__).resolve().parents[1]

    candidates = list(find_tmp_db_files(repo_root, recursive=args.recursive))
    if not candidates:
        print("No tmp_*.db files found.")
        return 0

    removed = 0
    for p in candidates:
        try:
            if args.dry_run:
                print(f"DRY-RUN would remove: {p}")
            else:
                print(f"Removing: {p}")
                p.unlink()
                removed += 1
        except Exception as exc:  # pragma: no cover - defensive cleanup
            print(f"Failed to remove {p}: {exc}")

    if args.dry_run:
        print(f"Found {len(candidates)} tmp_*.db file(s) (dry-run).")
    else:
        print(f"Removed {removed} tmp_*.db file(s).")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
