# Runbook — local validation and smoke tests

Commands below assume Windows PowerShell (as requested). Run from the repository root.

1) Install dependencies (if not already):

pip install -r requirements.txt

2) Run unit tests (fast subset):

pytest CLEAN_APP/tests -q

3) Run a focused integration test (auth registration):

pytest CLEAN_APP/tests/test_integration_comprehensive.py::TestAuthenticationFlow::test_user_registration_flow -q -s

4) Run the full test suite (may take a while):

pytest -q

5) Boot the app locally for manual smoke test:

$env:DATABASE_URL = "sqlite:///./local_dev.db"; python -m uvicorn CLEAN_APP.app.main:app --reload

Visit http://127.0.0.1:8000/ and check landing/login/signup flows.

Notes
- If tests fail due to SQLite locking on Windows, retry after a short wait; improve the test DB teardown in `CLEAN_APP/tests/conftest.py`.
- All preserved environment secrets should be supplied via env vars (no secrets in repo).
