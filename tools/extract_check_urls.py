import json
from pathlib import Path

PR_CHECKS = Path("tools") / "pr_checks.json"

if not PR_CHECKS.exists():
    raise SystemExit(2)

raw = PR_CHECKS.read_bytes()
if not raw:
    raise SystemExit(3)

decodings = ("utf-8", "utf-8-sig", "utf-16", "latin-1")
data = None
for enc in decodings:
    try:
        data = raw.decode(enc)
        break
    except Exception:
        continue

if data is None:
    raise SystemExit(4)

data = data.strip()
try:
    j = json.loads(data)
except json.JSONDecodeError:
    raise

fails = [c for c in j.get("statusCheckRollup", []) if c.get("conclusion") == "FAILURE"]
if not fails:
    raise SystemExit(0)

for _c in fails[:10]:
    pass
