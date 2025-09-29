Typing sweep — conservative `cast` + permissive Protocols

Scope
- Purpose: Replace raw `sqlite3.connect(...)` creation sites with a conservative, runtime-safe typing pattern across the codebase to improve static typing while preserving runtime behavior.
- Strategy: "Do both" hybrid approach — a single in-repo permissive shim (`app/_typing_shims.py`) of minimal Protocols, plus local, runtime-safe mitigations: `cast(ISyncConnection, sqlite3.connect(...))` or `typed_conn = cast(ISyncConnection, conn)` inside with-blocks.

What changed (high-level)
- Central typing shim: `app/_typing_shims.py` (added conservative Protocol shapes for ISyncConnection/ISyncCursor, expanded to include `executemany`, `fetchmany`, `lastrowid`, and `description`).
- App-level patches (representative):
  - `app/enterprise_analytics_reporting.py` — replaced uncasted connects in multiple helper functions.
  - `app/enterprise_database_async.py` — confirmed connection creation uses cast and is left as-is.
  - `app/core/database.py` — already used a cast-once pattern; validated and left unchanged.
  - `app/system_monitor.py`, `app/enterprise_health_dashboard.py`, `enterprise_analytics.py`, and other enterprise modules — validated and patched where raw connects were present.
- Tools & tests (optional): updated several helper scripts and `tests/conftest.py` to use the same conservative pattern to improve developer ergonomics.

Validation performed
- Per-file syntax checks (py_compile) for edited files.
- Per-file and targeted mypy runs after edits.
- Project-level mypy executed with excludes (CLEAN_APP/tools/tests excluded) — result: "Success: no issues found in 138 source files" (some informational notes about untyped function bodies remain).
- Quick test suite: `python run_tests.py` — 153 passed, 1 skipped.

Notes & rationale
- No runtime APIs changed — we only added `cast(...)` and small typing shim changes. All database `sqlite3` keyword args (timeout, check_same_thread) were preserved.
- We avoided adding repo .pyi stubs to prevent import collisions; a single in-repo shim `app/_typing_shims.py` centralizes permissive Protocols.
- Tests and tools were optionally updated to reduce local friction; the project-level mypy uses excludes to avoid duplicate module issues (e.g., CLEAN_APP tests).

Recommended next steps
- Optional: Run a focused mypy with `--check-untyped-defs` for critical modules to increase type coverage incrementally.
- Consider a follow-up sweep for other dynamic runtime APIs (e.g., Redis-like clients, external SDKs) using the same conservative pattern.
- Open a small PR with this branch and the summary, request a code-review focusing on the typing shim and any critical modules.

Contact
- If you'd like, I can generate a compact GitHub PR body summarizing the changes and include the test/mypy command outputs.
