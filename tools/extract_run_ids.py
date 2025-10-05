import json
from pathlib import Path

PR_CHECKS = Path("tools") / "pr_checks.json"
if not PR_CHECKS.exists():
    msg = f"File not found: {PR_CHECKS}"
    raise SystemExit(msg)

j = json.loads(PR_CHECKS.read_text(encoding="utf-8", errors="replace"))
for c in j.get("statusCheckRollup", []):
    run_url = c.get("detailsUrl") or ""
    # Try to parse run and job ids
    parts = run_url.rstrip("/").split("/")
    run_id = ""
    job_id = ""
    if "runs" in parts:
        try:
            idx = parts.index("runs")
            run_id = parts[idx + 1]
        except Exception:
            pass
    if "job" in parts:
        try:
            idx = parts.index("job")
            job_id = parts[idx + 1]
        except Exception:
            pass
