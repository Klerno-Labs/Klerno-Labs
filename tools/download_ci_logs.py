import json
import re
import subprocess
from pathlib import Path

PR_CHECKS = Path("tools") / "pr_checks.json"
OUT_DIR = Path("tools") / "ci_logs"

if not PR_CHECKS.exists():
    raise SystemExit(f"Missing {PR_CHECKS}")

text = PR_CHECKS.read_text(encoding="utf-8", errors="replace")
# attempt to extract the JSON object by finding the first '{' and last '}'
start = text.find("{")
end = text.rfind("}")
if start == -1 or end == -1 or end <= start:
    raise SystemExit("Could not find JSON object in pr_checks.json")
json_text = text[start : end + 1]
print("DEBUG: extracted json length=", len(json_text))
print("DEBUG: snippet=")
print(json_text[:300])
try:
    j = json.loads(json_text)
except Exception as exc:
    raise SystemExit(f"Failed to parse JSON: {exc}") from exc

fails = [c for c in j.get("statusCheckRollup", []) if c.get("conclusion") == "FAILURE"]
if not fails:
    print("No failing checks found")
    raise SystemExit(0)

OUT_DIR.mkdir(parents=True, exist_ok=True)

downloaded = 0
for c in fails[:3]:
    url = c.get("detailsUrl") or ""
    # extract run id from url like /actions/runs/123 or /runs/123
    m = re.search(r"/runs/(\d+)", url)
    run_id = m.group(1) if m else ""
    if not run_id:
        print("Could not parse run id from", url)
        continue
    target = OUT_DIR / run_id
    target.mkdir(parents=True, exist_ok=True)
    print(f"Downloading run {run_id} -> {target}")
    # Call gh run download
    try:
        res = subprocess.run(
            ["gh", "run", "download", run_id, "--dir", str(target)],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        print("gh CLI not found in PATH; aborting")
        raise SystemExit(2) from None
    if res.returncode != 0:
        print("gh run download failed for", run_id)
        print(res.stdout)
        print(res.stderr)
    else:
        print("Downloaded run", run_id)
        downloaded += 1

print(f"Done. downloaded {downloaded} runs to {OUT_DIR}")
