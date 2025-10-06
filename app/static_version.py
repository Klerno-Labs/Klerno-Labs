"""Static asset version helper.

Resolves a stable STATIC_VERSION string to be appended to static asset URLs.
Order of precedence:
1. STATIC_VERSION environment variable (explicit control in CI/CD)
2. Current git commit short hash, if available
3. Unix timestamp fallback (dev-only best effort)
"""

from __future__ import annotations

import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path

# Cache computed version to avoid repeated work
_cached_version: str | None = None


def _git_short_sha(repo_root: Path) -> str | None:
    # Try git command first
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(repo_root),
            stderr=subprocess.DEVNULL,
        )
        sha = out.decode().strip()
        if sha:
            return sha
    except Exception:
        pass

    # Try reading .git/HEAD manually
    try:
        head_path = repo_root / ".git" / "HEAD"
        if head_path.exists():
            head = head_path.read_text(encoding="utf-8").strip()
            if head.startswith("ref:"):
                ref = head.split(" ", 1)[1].strip()
                ref_path = repo_root / ".git" / ref
                if ref_path.exists():
                    full_sha = ref_path.read_text(encoding="utf-8").strip()
                    if full_sha:
                        return full_sha[:7]
            else:
                # HEAD contains a detached commit sha
                if head:
                    return head[:7]
    except Exception:
        pass
    return None


def get_static_version() -> str:
    global _cached_version
    if _cached_version:
        return _cached_version

    # 1) ENV wins
    env = os.getenv("STATIC_VERSION")
    if env:
        _cached_version = env
        return _cached_version

    # 1b) Render’s deploy metadata if available (set automatically by Render)
    for k in ("RENDER_GIT_COMMIT_SHA", "RENDER_GIT_COMMIT"):
        val = os.getenv(k)
        if val:
            _cached_version = val[:7]
            return _cached_version

    # 2) Git short SHA when available
    try:
        repo_root = Path(__file__).resolve().parent.parent
        sha = _git_short_sha(repo_root)
        if sha:
            _cached_version = sha
            return _cached_version
    except Exception:
        pass

    # 3) Fallback to timestamp (dev)
    _cached_version = str(int(datetime.now(UTC).timestamp()))
    return _cached_version
