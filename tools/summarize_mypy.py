"""
Run mypy on `app` and summarize error counts by file.
Saves full mypy output to tools/mypy_full.txt and prints top 20 files with counts and sample errors.
"""

"""
Run mypy on `app` and summarize error counts by file.
Saves full mypy output to tools/mypy_full.txt and prints top 20 files with counts and sample errors.
"""

import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path


def run_mypy():
    cmd = [sys.executable, "-m", "mypy", "app", "--show-error-codes"]
    print("Running:", " ".join(cmd))
    p = subprocess.run(cmd, capture_output=True, text=True)
    out = p.stdout + p.stderr
    path = Path("tools/mypy_full.txt")
    with path.open("w", encoding="utf-8") as f:
        f.write(out)
    return out, p.returncode


def summarize(out, top_n=20, sample_per_file=3):
    pattern = re.compile(r"^(.*?):(\d+): (error|note): (.*)$", re.MULTILINE)
    errors_by_file = defaultdict(list)
    for m in pattern.finditer(out):
        path = m.group(1).strip()
        line = m.group(2)
        kind = m.group(3)
        msg = m.group(4).strip()
        # only count 'error' lines (not notes)
        if kind == "error":
            errors_by_file[path].append((int(line), msg))
    totals = [(len(v), k) for k, v in errors_by_file.items()]
    totals.sort(reverse=True)
    total_errors = sum(c for c, _ in totals)
    print(f"Found {total_errors} errors across {len(totals)} files")
    print("\nTop files:")
    for count, path in totals[:top_n]:
        print(f"{count:4d}\t{path}")
        sample = errors_by_file[path][:sample_per_file]
        for ln, msg in sample:
            print(f"    {ln}: {msg}")
    if len(totals) == 0:
        print("No errors found")


if __name__ == "__main__":
    out, code = run_mypy()
    summarize(out)
    sys.exit(code)
