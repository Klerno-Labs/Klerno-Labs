## ci: mypy cleanup, ruff fixes, Bandit artifact, and minor runtime shims

This PR contains a focused set of minimal, low-risk changes to make CI output actionable
and remove noisy static-checker/linters issues so real errors surface in CI.

Summary of changes
- Removed unused/incorrect `# type: ignore` comments across several files.
- Replaced fragile module attribute assignments with `setattr(...)` in dynamic shims
  (preview_server, enterprise_preview, `app.__init__`, `sitecustomize`) so mypy no longer
  reports `attr-defined` false-positives.
- Reworked a few runtime imports to be explicit/dynamic where needed (e.g., BlockUserRequest
  constructed via runtime import in `app/system_monitor.py`).
- Removed redundant casts (e.g. connection cast in pool initialization) and small syntax fixes.
- Ran `ruff --fix` and applied style corrections across the repository.
- Ran Bandit and saved the JSON artifact to `.artifacts/bandit_report.json`.

Why
- The primary goal was to reproduce CI failures locally, triage logs, and land minimal fixes
  to make the PR green. Much of the earlier CI noise was caused by unused type-ignore directives
  and attr-defined messages from dynamic shims. Reducing that noise makes CI actionable.

Validation performed
- `python -m mypy --config-file mypy.ini .`  -> clean (no issues across 131 files)
- `python -m mypy --config-file mypy.ini --check-untyped-defs .` -> clean
- `python -m ruff check --fix .` -> 14 fixes applied
- `python -m bandit -r -f json -o .artifacts/bandit_report.json .` -> JSON artifact generated
- `python -m pytest -q` -> 154 passed, 1 skipped, 1 warning

Notes and follow-ups
- I did not run external network-dependent checks. If you want, I can open the PR and watch GitHub Actions run. `gh` CLI is not available in this environment; use the browser or local `gh` to open the PR.
- Optional next: run `mypy --strict` or add `--check-untyped-defs` permanently to CI if you want stricter checks.

How to open the PR locally
If you have the GitHub CLI installed locally run:

```powershell
gh pr create --base main --head ci/enterprise-run-migrations-pr25 --title "ci: mypy cleanup, ruff fixes, Bandit artifact" --body-file PR_BODY_CI_TYPECLEANUP.md
```

Or open the compare page in a browser and create the PR: replace the owner/repo path with the repo
hosting this branch if different.

Artifact
- `.artifacts/bandit_report.json` (committed) contains the Bandit JSON report produced during the run.

If you'd like I can now open the PR (if you install/allow a gh token) or I can open it in the browser for you.
