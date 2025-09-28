Typing sweep: conservative DB typing and permissive Protocol shim

Summary
- Replaced direct sqlite3 connection sites with a conservative runtime-safe pattern:
  - Use `from typing import cast` and `cast(ISyncConnection, sqlite3.connect(...))` at creation sites
  - For with-blocks: `with sqlite3.connect(...) as conn: typed_conn = cast(ISyncConnection, conn)`
- Centralized permissive Protocols in `app/_typing_shims.py` and extended them with commonly-used members (`executemany`, `fetchmany`, `lastrowid`, `description`) to reduce type noise.

Files touched (high-level)
- app/_typing_shims.py (new shapes for ISyncConnection/ISyncCursor)
- app/enterprise_analytics_reporting.py (several connection sites)
- app/enterprise_database_async.py (validated; creates casted connections)
- app/core/database.py (validated existing cast usage)
- app/system_monitor.py (validated typed locals)
- app/store.py (validated)
- tools/* and tests/* (optional: tests/conftest.py, tools helpers updated for dev ergonomics)

Validation
- Per-file syntax checks (py_compile) on modified files.
- Project mypy run (with excludes in pyproject.toml): Success for the intended checked set (138 source files). Informational notes remain about untyped function bodies.
- Quick test suite: 153 passed, 1 skipped.

Notes for reviewers
- No runtime behavior changed — all edits use `cast()` and runtime DB args preserved.
- We intentionally avoided adding .pyi stubs; prefer single in-repo shim for permissive Protocols.
- Tools/tests updated to reduce local friction; they can be reverted if preferred.

Suggested reviewers
- Core maintainers for DB layer: @owner/db-team
- Type-checking/CI: @owner/infra

How to test locally
1) Activate venv and run tests:

```powershell
python -m venv .venv-py311; .\.venv-py311\Scripts\Activate.ps1; pip install -r requirements.txt
python run_tests.py
```

2) Run mypy (project-level) with excludes if desired:

```powershell
python -m mypy . --config-file pyproject.toml --exclude "CLEAN_APP|tools|tests"
```

PR checklist
- [ ] Verify CI mypy job uses configured excludes
- [ ] Sanity-run smoke tests on a fresh env
- [ ] Optional: ask reviewer whether tools/tests edits should be kept or reverted

Mypy output (summary)
```
Success: no issues found in 138 source files
Notes (informational): several files contain untyped function bodies; consider using --check-untyped-defs for stricter checking.
```
