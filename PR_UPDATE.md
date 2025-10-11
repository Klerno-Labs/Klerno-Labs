Summary of changes and verification

This PR contains a set of small, safe fixes to restore application testability and clean up typing and style issues.

What I changed (high level)
- Restored a minimal `templates/landing-clean.html` so the landing page returns non-empty HTML (prevents empty-template regressions).
- Fixed several mypy warnings by removing unnecessary `# type: ignore` comments and applying narrow type adjustments.
- Applied ruff autofixes across the repo and made a few small manual edits (replace `try`/`except: pass` with `contextlib.suppress`, add exception chaining `from None` where appropriate, and use `setattr` for the openapi assignment with a `# noqa: B010` comment to keep mypy satisfied).

Files changed (not exhaustive but key files):
- `templates/landing-clean.html` (added minimal HTML)
- `app/main.py` (safety headers, openapi assignment, small exception handling adjustments)
- `app/logging_config.py` (optional import adjustments)
- `app/auth.py` (minor audit/logging fixes)
- `app/store.py` (suppress exception style change)
- `app/models.py` (typing import normalization)

Verification performed
- Tests: 220 passed, 2 skipped (full pytest run in project venv)
- Type checking: mypy reports "Success: no issues found in 108 source files"
- Linting: ran `ruff check . --fix` and applied autofixes (all ruff checks pass locally)

Notes and recommended follow-ups
- The project's `flake8` in the current venv previously failed due to a pycodestyle plugin/version mismatch (ImportError). To reduce CI/dev friction I recommend either:
  1) Migrate CI/local tooling to use `ruff` (fast, single tool that covers formatting and linting), or
  2) Pin `flake8` and `pycodestyle` dev dependency versions and ensure plugins are compatible in CI.

Commands I ran locally (PowerShell)
```powershell
& .\.venv-1\Scripts\python.exe -m pytest -q
& .\.venv-1\Scripts\python.exe -m mypy app --show-error-codes
& .\.venv-1\Scripts\python.exe -m ruff check .
& .\.venv-1\Scripts\python.exe -m ruff check . --fix
```

If you'd like
- I can update CI (GitHub Actions) to run `ruff` instead of `flake8`, or pin dev deps for flake8.
- I can split style-only changes into a separate PR if you prefer.
- I can squash/rebase these commits into a single tidy commit before merging.

Status: ready for review. Tests and mypy are green; style fixes applied and pushed to `fix/tests-and-mypy`.
