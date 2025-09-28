PR: typing and small runtime hardening (chore/dev-dx)

Summary
-------
This PR tightens typing and adds a few defensive runtime guards across the codebase to make incremental progress towards stricter static checking and safer runtime behavior.

What changed
------------
- Introduced `UserDict` TypedDict in `app/store.py` and normalized `_row_to_user` to return a consistent typed shape.
- Tightened several function signatures and dependency return types in:
  - `app/deps.py` (support `UserDict` in dependency signatures and return values)
  - `app/auth.py` (narrowed totp_secret usage and coerced password hash to `str` before verification)
- Added small runtime guards/coercions (e.g., iterate over `wallet_addresses or []`, shallow-copy user dict before adding dynamic keys such as `xrpl_subscription`).

Files touched (high-level)
-------------------------
- app/store.py  — TypedDict, normalization, wallet handling
- app/deps.py   — dependency signature types, small augmentation change
- app/auth.py   — defensive guards for MFA and password verification
- Several mypy runs and iterative fixes across the `app` package to progressively enable `--check-untyped-defs` on high-value modules.

Verification
-----------
- Ran pytest: 153 passed, 1 skipped
- Ran mypy across the `app` package and many `--check-untyped-defs` batches. After iterative fixes, `app` and prioritized modules reported no issues under stricter checks.

Notes for reviewers
------------------
- Most changes are low-risk: they coerce/normalize values already handled at runtime or add defensive checks.
- The TypedDict addition tightens the expected user record shape; callers that add dynamic keys now shallow-copy the dict to avoid TypedDict mutation issues.

Next steps
---------
- Continue incremental tightening by running `--check-untyped-defs` on remaining modules in small batches.
- Optionally enable per-module stricter mypy config to enforce `disallow_untyped_defs` gradually.
- Add lightweight unit tests for newly-typed behaviors if desired.

How to test locally
------------------
# (run in project root)

# Run tests
.venv-py311\Scripts\python.exe -m pytest -q

# Run mypy for app package
.venv-py311\Scripts\python.exe -m mypy --show-error-codes --pretty app

Merge notes
-----------
This is intentionally conservative. If you prefer, we can split the PR into a) `UserDict` + normalization and b) follow-up guard/type fixes.

Authored-by: chore/dev-dx automation
