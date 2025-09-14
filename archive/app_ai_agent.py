"""
Archived from app/ai_agent.py
"""
from __future__ import annotations

import difflib
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime, timezone

import yaml

ROOT = Path(__file__).resolve().parents[1]

@dataclass
class Suggestion:
	file: str         # repo-relative, POSIX
	before: str
	after: str
	rationale: str

def load_policy() -> Dict[str, Any]:
	p = ROOT / "automation" / "policy.yaml"
	if not p.exists():
		# No policy? Act as "deny all" to be safe.
		return {"allowed_paths": []}
	try:
		return yaml.safe_load(p.read_text(encoding="utf-8")) or {"allowed_paths": []}
	except Exception as e:
		# Malformed policy -> deny all
		print(f"[policy] Failed to load policy.yaml: {e}")
		return {"allowed_paths": []}

def _insert_future_annotations(content: str) -> str:
	lines = content.splitlines()
	for i, ln in enumerate(lines[:5]):
		if ln.strip() == "from __future__ import annotations":
			return content
	# add at top, after shebang if present
	if lines and lines[0].startswith("#!/"):
		return "\n".join([lines[0], "from __future__ import annotations", *lines[1:]])
	return "\n".join(["from __future__ import annotations", *lines])

def llm_suggest(file_path: Path, content: str) -> List[Suggestion]:
	# This was a proposal-only tool to suggest improvements via LLM.
	# Keep as a no-op placeholder in the archive.
	return []

def bounded_change_allowed(policy: Dict[str, Any], abs_path: Path) -> bool:
	allowed = policy.get("allowed_paths") or []
	rel = abs_path.relative_to(ROOT).as_posix()
	return any(rel.startswith(p.rstrip("/")) for p in allowed)

def make_patch(before: str, after: str, file_label: str) -> str:
	diff = difflib.unified_diff(
		before.splitlines(keepends=True),
		after.splitlines(keepends=True),
		fromfile=f"a/{file_label}",
		tofile=f"b/{file_label}",
	)
	return "".join(diff)

def propose_changes() -> None:
	policy = load_policy()
	proposals_dir = ROOT / "automation" / "proposals"
	patches_dir = ROOT / "automation" / "patches"
	proposals_dir.mkdir(parents=True, exist_ok=True)
	patches_dir.mkdir(parents=True, exist_ok=True)

	for p in (ROOT / "app").rglob("*.py"):
		if not bounded_change_allowed(policy, p):
			continue

		content = p.read_text(encoding="utf-8")
		for sug in llm_suggest(p, content):
			patch = make_patch(sug.before, sug.after, sug.file)
			stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
			uid = uuid.uuid4().hex[:8]
			proposals_path = proposals_dir / f"proposal_{stamp}_{uid}_{p.stem}.md"
			patches_path = patches_dir / f"patch_{stamp}_{uid}_{p.stem}.patch"

			proposals_path.write_text(
				f"# Improvement Proposal\n\n"
				f"**File:** `{sug.file}`\n\n"
				f"**Rationale:** {sug.rationale}\n\n"
				f"**How to apply:**\n"
				f"```bash\ngit apply automation/patches/{patches_path.name}\n```\n",
				encoding="utf-8",
			)
			patches_path.write_text(patch, encoding="utf-8")

if __name__ == "__main__":
	propose_changes()