import json
from pathlib import Path

PR_CHECKS = Path("tools") / "pr_checks.json"

if not PR_CHECKS.exists():
    print(f"File not found: {PR_CHECKS.resolve()}")
    raise SystemExit(2)

raw = PR_CHECKS.read_bytes()
if not raw:
    print(f"File is empty: {PR_CHECKS.resolve()}")
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
    print(f"Unable to decode {PR_CHECKS.resolve()} with tried encodings: {decodings}")
    raise SystemExit(4)

data = data.strip()
try:
    j = json.loads(data)
except json.JSONDecodeError as exc:
    print(f"Failed to parse JSON: {exc}")
    raise

fails = [c for c in j.get("statusCheckRollup", []) if c.get("conclusion") == "FAILURE"]
if not fails:
    print("No failing checks found in statusCheckRollup")
    raise SystemExit(0)

for c in fails[:10]:
    print(c.get("detailsUrl"))
