# PR: chore/dev-dx — Developer DX, readiness checks, smoke tests, lint/type fixes

## What changed
------------
- Added readiness/import-time checks (`scripts/check_prod_readiness.py`) and unit tests.
- Restored/added developer tooling: local DB seeder, login probe, and a local smoke runner (`tools/*`).
- Hardened enterprise entrypoints to avoid import-time failures in minimal environments (guarded imports and runtime shims).
- Applied ruff autofixes and a number of small mypy-directed changes to reduce static analysis noise.

## Tests & validation
------------------
- `python -m mypy .` => no blocking errors (informational notes about untyped function bodies remain).
- `python -m ruff check . --fix` iteratively run; most issues fixed or intentionally suppressed.
- `python -m pytest -q` => `153 passed, 1 skipped`.

## Why these changes
-----------------
The repo had several import-time fragilities and a poor local dev onboarding flow (no deterministic way to seed a dev user or run smoke tests). The changes make local development easier and make CI fail fast on import-time issues.

## Remaining technical debt
------------------------
- Many untyped function bodies across `app/` modules (informational mypy notes). Recommend a follow-up typed-refactor focused on critical modules.
- A few ruff warnings in tests that intentionally use broad exception assertions; leaving tests unchanged to preserve behavior.

## Next steps
----------
- Optionally squash these commits and open a draft PR for review.
- If you want, I can open the PR and assign reviewers and add the changelog to the PR body.
