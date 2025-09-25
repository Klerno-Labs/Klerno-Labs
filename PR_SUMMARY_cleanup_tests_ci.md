PR: cleanup/tests-ci

This branch contains small, surgical hygiene changes intended to reduce CI noise and improve debugging:

- Preserve exception chaining for easier debugging
- Minor safety fixes in `app/main.py`
- Local verification: `pytest` passed in the project's venv

Use the contents of `PR_BODY_cleanup_tests_ci.md` for a detailed description when opening the PR.
