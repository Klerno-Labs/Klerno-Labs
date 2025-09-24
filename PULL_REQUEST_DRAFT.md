Title: ci: fix pandas import-time circulars; add CI and import-safety test

Summary:
This PR defers heavy `pandas` imports to runtime in modules that are imported during test collection, adds a minimal GitHub Actions CI workflow to run `mypy` and `pytest`, and introduces an import-safety test to catch regressions where modules import heavy dependencies at module import-time.

What I changed:
- Added `.github/workflows/ci.yml` to run `mypy` and `pytest` on push/PR to `main`/`master`.
- Added `tests/test_imports.py` — ensures `app.analytics` and `enterprise_analytics` don't import `pandas` at import time.
- Added lazy import guard `_ensure_pandas()` calls in several modules (`app/admin.py`, `app/enterprise_analytics_reporting.py`) to avoid pandas import at module import-time.

Why:
- During local test runs, pytest collection failed due to a pandas import-time circular import. Deferring pandas import fixes the failure and reduces test fragility.
- The CI workflow ensures future changes are validated automatically.

Notes:
- I attempted to push the branch `cleanup/tests-ci` to `origin`, but the remote requested interactive authentication from your environment. Please run the following locally to complete the push and open the PR if you'd like me to create the PR on your behalf:

```powershell
git push origin cleanup/tests-ci
# then, using GitHub CLI if available:
gh pr create --title "ci: fix pandas import-time circulars; add CI and import-safety test" --body-file PULL_REQUEST_DRAFT.md --base main
```

If you'd like, I can also wait while you authenticate and complete the push, or you can copy the commands above and run them locally.
