Title: chore/dev-dx — Developer DX, readiness checks, smoke tests, lint/type fixes

Summary
-------
This branch modernizes developer experience and hardens import-time behavior so CI fails fast on initialization problems. It adds readiness checks, local developer tools (DB seed, login probe, smoke runner), small static-analysis fixes, and documentation.

Changes
-------
- scripts/check_prod_readiness.py: import-time readiness checks and unit test.
- tools/: added/modernized `seed_local_db.py`, `login_probe.py`, `run_local_smoke.py`, `prod_smoke_test.py`, and helper tools.
- app/ and enterprise entrypoints: guarded imports, runtime shims to avoid import-time crashes in minimal environments.
- performance middleware: safer response handling.
- Various ruff/mypy-friendly edits across the repo.
- CHANGES_FOR_DEV.md and PR_DESCRIPTION.md added.

Tests & validation
------------------
- mypy: no blocking errors (informational notes about untyped functions remain).
- ruff: autofix and targeted edits applied; remaining warnings are test-intentional.
- pytest: 153 passed, 1 skipped.

Checklist for reviewers
-----------------------
- [ ] Review readiness script and unit test for false positives/over-strict checks.
- [ ] Confirm dev seeder/login probe are safe to run locally (no destructive DB ops on production-like configs).
- [ ] Verify smoke test wiring and webhook signing logic meets security expectations (secrets required in CI).
- [ ] Approve targeted mypy/ruff suppressions (narrow, well-justified usages).

Follow-ups (post-merge or separate PR)
-------------------------------------
- Run stricter mypy pass with `--check-untyped-defs` and triage findings (large effort; propose separate PR).
- Consider refactoring dynamic shims and builtins injection to a single compatibility module for clarity.
- Optional: fix test lints for broad Exception assertions.

How to open the draft PR
------------------------
1. Push this branch to origin (if not already pushed):

```powershell
# from repo root
git add -A ; git commit -m "chore(dev-dx): developer DX, readiness checks, smoke tests, small typing/lint fixes" ; git push origin chore/dev-dx
```

2. Open a draft PR in the repository UI (compare branch `chore/dev-dx` -> `main`) and paste this file as the PR body if helpful.

Contact
-------
If you'd like, I can open the draft PR for you and assign reviewers. Reply with "open PR" and I will prepare the PR body and open it as draft.
