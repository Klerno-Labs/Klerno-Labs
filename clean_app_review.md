# CLEAN_APP Review

This document summarizes a focused audit of `CLEAN_APP/` (source of truth) and lists files assessed as Good / Needs improvement / Critical, with one-line reasons and suggested fixes. I limited changes to minimal, non-invasive fixes so the app boots and tests run.

Good
- `CLEAN_APP/app/main.py` — Central FastAPI app and router registration present; clear lifespan and middleware. (Good)
- `CLEAN_APP/app/auth.py` — Comprehensive auth endpoints (signup/login/me) with clear schema models and cookie handling. (Good)
- `CLEAN_APP/app/integrations/` — Present and modular (Good)
- `CLEAN_APP/tests/` — Focused test suite organized; pytest.ini restricts collection.

Needs improvement
- `CLEAN_APP/app/security/__init__.py` — Missing a couple of compatibility functions (`preview_api_key`, `rotate_api_key`) that other modules import; added minimal shims. Suggested: consolidate security helpers and document exported API.
- `CLEAN_APP/app/main.py` — Legacy compatibility aliases were added; refactor plan: consolidate alias handling into `app/compat.py` to keep main clean.

Critical
- Database test fixtures in `CLEAN_APP/tests/conftest.py` — Windows file locking and temp DB cleanup can fail; tests currently use retry-on-delete scheme but further cleanup required. Fix: close all connections explicitly and use tempfile with context managers.

Next steps / fixes applied
- Added `deletion_audit.md` (phase A snapshot) and created `Trash me/` for quarantine.
- Added compatibility shims for missing security helpers.

Recommendations to reach top 0.01%
- Run full test-suite and iterate on any failures (auth integration tests currently failing prior to fixes; focusing now on auth registration).
- Consolidate duplicate code identified in Deletion/ into CLEAN_APP and remove duplicates.
- Improve DB fixture teardown and add unit tests that exercise the full auth/login flow in an isolated manner.

