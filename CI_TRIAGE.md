# CI Triage Checklist

Quick resolution guide for failing CI workflows

## 1. Reproduce locally

- Pull the PR branch and run CI steps locally in the venv.

### Commands (PowerShell)

```powershell
# activate venv (if not activated)
& ".\.venv-py311\Scripts\Activate.ps1"
# Run linters
& ".\.venv-py311\Scripts\ruff.exe" check .
& ".\.venv-py311\Scripts\mypy.exe" .
& ".\.venv-py311\Scripts\python.exe" -m pytest -q
```

## 2. Common failures & fixes

- Import-time DB/env problems: ensure `DATABASE_URL` is set before importing modules; run tests with `DATABASE_URL=sqlite:///tmp/test.db`.
- SQLite locking: set `PRAGMA journal_mode=WAL` and `timeout=5.0` in `_sqlite_conn()` (already applied). Increase timeout if CI shows lock timeouts.
- Heavy imports slowing/timeouting test collection: ensure large libs are imported lazily.

## 3. When logs show a failing test

- Copy the failing test name and run only that test locally: `python -m pytest tests/path/to/test_file.py::test_name -q`.
- Use `-k` to run related tests: `pytest -k "wallet and create" -q`.

## 4. When linters fail

- Run the specific linter command locally and fix or add a targeted `# noqa` or `# type: ignore` with a brief comment.

## 5. Share logs

- When CI fails, paste the failing workflow step logs here and I will provide a patch.
