# Dev auth & seeding

This document explains how to seed a development admin user, run the inspection tools, and run the automated tests that exercise the login flows.

Quick steps

- Seed dev admin automatically when starting the app locally:
  - Set these env vars before starting the app if you want custom credentials:
    - `DEV_ADMIN_EMAIL` (default `klerno@outlook.com`)
    - `DEV_ADMIN_PASSWORD` (default `Labs2025`)
  - Start the app (example):

```powershell
$env:DEV_ADMIN_EMAIL='dev@example.com'; $env:DEV_ADMIN_PASSWORD='MyStrongPass123!'; .\.venv-py311\Scripts\python.exe -m uvicorn app.main:app --reload
```

- Run the interactive inspector (creates a temporary sqlite DB and seeds users):

```powershell
$env:AUTH_DEBUG='1'; $env:STORE_DEBUG='1'; .\.venv-py311\Scripts\python.exe tools\inspect_login.py
```

- Run the pytest for auth flows (they create a temp DB and clean up automatically):

```powershell
.\.venv-py311\Scripts\python.exe -m pytest tests/test_auth_flow.py -q
.\.venv-py311\Scripts\python.exe -m pytest tests/test_auth_form_and_cookie.py -q
```

Notes

- Logging is centralized in `app/logging_config.py`. To enable debug output for local development set `APP_ENV=dev` or `settings.app_env` accordingly so the logger level is DEBUG.
- The inspector and tests set `DATABASE_URL` to a temporary sqlite file before importing app modules. If you run code in an interactive shell make sure to set `DATABASE_URL` before importing `app` to avoid mismatched DB paths.
- After troubleshooting, remove or avoid setting `AUTH_DEBUG`/`STORE_DEBUG` and rely on logging levels instead.
