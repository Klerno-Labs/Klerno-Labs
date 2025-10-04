# Klerno Labs - Clean Application

This is the **clean, consolidated version** of the Klerno Labs Enterprise Transaction Analysis Platform. This version contains only the essential core functionality without the duplicate files found in the main project.

## ✨ What's Different

- **Single Authentication System**: Consolidated from 5 conflicting auth files to 1 clean auth.py
- **Unified Landing Page**: One cohesive design instead of multiple conflicting templates
- **Streamlined Codebase**: Essential functionality only, no duplicates
- **Clean Architecture**: FastAPI + SQLite + Bootstrap for simplicity

## 🚀 Quick Start

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Start the Application**:
   ```bash
   python start_clean.py
   ```

3. **Access the Application**:
   - **Landing Page**: [http://localhost:8000](http://localhost:8000)
   - **Login**: [http://localhost:8000/auth/login](http://localhost:8000/auth/login)
   - **Admin Dashboard**: [http://localhost:8000/admin](http://localhost:8000/admin) (after login as admin)

## Development

Dev / test notes
---------------

For local testing we use a Python 3.11 virtual environment to keep
dependency wheels compatible with the project's pinned packages. A
recommended workflow on Windows PowerShell:

```powershell
python -m venv .venv-py311
. .\.venv-py311\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pytest -q
```

The `requirements.txt` is runtime-only. Test and developer-only packages
are listed in `dev-requirements.txt`. To install just the test helpers
locally run:

```powershell
python -m pip install -r dev-requirements.txt
```

### Migration note

`app/legacy_helpers.py` is retained as a small compatibility shim for
older tests that import `create_access_token`/`verify_token` from
builtins. Teams should migrate tests and code to import the functions
directly from `app.auth` or `app.security_session` and then the shim can
be removed. For local installs of only the test helpers use:

```powershell
python -m pip install -r dev-requirements.txt
```

### CI status

![Core CI](https://github.com/Klerno-Labs/Klerno-Labs/actions/workflows/core-ci.yml/badge.svg)


## 🔑 JWT Rotation & Refresh Tokens

Klerno Labs uses short-lived access tokens (default 15 minutes) and long-lived refresh tokens (default 7 days) for authentication. Refresh tokens are single-use and are rotated on each refresh. Revoked/used tokens are tracked until expiry.

- **Access token lifetime**: Configurable via `ACCESS_TOKEN_EXPIRE_MINUTES` (default: 15)
- **Refresh token lifetime**: Configurable via `REFRESH_TOKEN_EXPIRE_DAYS` (default: 7)
- **Redis support**: If `USE_REDIS_REFRESH=true` and `REDIS_URL` is set, refresh tokens are stored in Redis for distributed deployments; otherwise, in-memory fallback is used.
- **Endpoints**:
  - `/auth/token/refresh`: Exchange a valid refresh token for a new access+refresh token pair (rotates refresh token)
  - `/auth/token/revoke`: Revoke a refresh token (logout)

**Environment variables:**

```
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
USE_REDIS_REFRESH=true
REDIS_URL=redis://localhost:6379
```

**Security notes:**
- Refresh tokens are single-use; reusing an old token after rotation will fail.
- If Redis is unavailable, the system falls back to in-memory storage (ephemeral, not suitable for multi-instance production).
- Access tokens should be sent as Bearer tokens; refresh tokens are returned in API responses and should be stored securely by the client.

## 👤 First Time Setup

1. Visit [http://localhost:8000/auth/signup](http://localhost:8000/auth/signup)
2. Create your account (first user becomes admin automatically)
3. Login and access the admin dashboard

## 📁 Project Structure

```
CLEAN_APP/
├── app/
│   ├── __init__.py          # Package init
│   ├── main.py             # FastAPI application
│   ├── auth.py             # Authentication system
│   ├── admin.py            # Admin panel
│   ├── models.py           # Data models
│   ├── store.py            # Database operations
│   └── settings.py         # Configuration
├── templates/
│   ├── base.html           # Base template
│   ├── landing.html        # Landing page
│   ├── login.html          # Login form
│   ├── signup.html         # Signup form
│   ├── admin.html          # Admin dashboard
│   └── dashboard.html      # User dashboard
├── static/                 # Static files (CSS, JS, images)
├── data/                   # SQLite database (auto-created)
├── requirements.txt        # Python dependencies
├── start_clean.py         # Startup script
└── README.md              # This file
```

## 🔧 Key Features

- **Authentication**: Secure login/signup with bcrypt password hashing
- **Admin Panel**: User management and system administration
- **Responsive Design**: Bootstrap-based responsive UI
- **Database**: SQLite for simplicity (easily upgradeable to PostgreSQL)
- **API**: RESTful FastAPI backend

## 🛡️ Security Features

- **Password Hashing**: bcrypt for secure password storage
- **Session Management**: FastAPI session middleware
- **Role-Based Access**: Admin/User role separation
- **Input Validation**: Pydantic models for API validation
- **Hardened Cookies**: `SameSite=Strict` and secure flag automatically enabled outside development
- **Secret Validation**: Startup guard rejects weak or default JWT secrets in non-development environments

## 🔄 Migration from Original Project

This clean version was created by:
1. Identifying and removing 254 duplicate files from the original 256-file project
2. Consolidating conflicting authentication systems
3. Creating a unified landing page design
4. Streamlining the database schema
5. Removing unnecessary complexity

## 📈 Next Steps

From this clean foundation, you can:

- Add blockchain analysis features
- Implement transaction monitoring
- Add more sophisticated user management
- Integrate with external APIs
- Add real-time dashboard features

## One-line deploy / run

For a quick production-ish run (use real secrets in env):

```powershell
# build image
docker build -t klerno-app .
# run with env (example)
docker run --rm -e APP_ENV=production -e JWT_SECRET='your-very-strong-secret' -p 8000:8000 klerno-app
```

For more detailed steps and rollback instructions, see `docs/DEPLOY_RUNBOOK.md`.

## 🆘 Support

This clean application provides the same core functionality as the original project but with:

- 99% fewer files
- No conflicting systems
- Clear architecture
- Easy maintenance

The original project structure remains available for reference in the parent directory.

## Run locally (Windows PowerShell)

If you want to start the app locally and quickly verify the login flow (dev-only admin credentials are created automatically on first run), follow these steps in PowerShell:

```powershell
# Create and activate a Python 3.11 venv (one-time)
python -m venv .venv-py311
. .\.venv-py311\Scripts\Activate.ps1

# Install runtime deps (use dev-requirements for test helpers if needed)
python -m pip install -r requirements.txt

# Start the server in the background (keeps this shell free)
Start-Process -FilePath ".\.venv-py311\Scripts\python.exe" -ArgumentList '-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8000','--log-level','info' -NoNewWindow

# Run a small smoke-test (optional)
. .\.venv-py311\Scripts\python.exe scripts\smoke_test.py
```

Default dev admin credentials (local development only):

- email: `klerno@outlook.com`
- password: `Labs2025`

Troubleshooting:

- If the server exits immediately, inspect the terminal that started uvicorn for startup logs. Common causes: missing python packages, or a locked port; install requirements and retry.
- If templates fail to render, ensure the working directory is the project root so the `templates/` folder is on the app path.

## CI and Contributing

This repository includes a CI workflow that runs import-safety checks, `mypy`, and `pytest` on pull requests to `main`.

To create a PR from a feature branch (example using the current hardening work):

```powershell
# Create a descriptive branch
git checkout -b chore/ci-observability-hardening

# Push and open PR (requires GitHub CLI)
git push -u origin chore/ci-observability-hardening
gh pr create --title "chore(ci+observability+security): consolidate workflows; add readiness & metrics" --body-file PULL_REQUEST_DRAFT.md --base main
```

The unified `core-ci.yml` replaces the prior fragmented `ci.yml`, `ci-minimal.yml`, and `pytest.yml` workflows (now removed). Use one branch per logical change set to keep reviews focused.

## Local development helper files

Two helper files were added to make running locally easier:

- `.env.example` — copy to `.env` or read and set the listed environment variables. It lists `X_API_KEY`, `JWT_SECRET`, `DATABASE_URL`, and optional integration keys (OpenAI, SendGrid, Stripe, BSC).
- `start-local.ps1` — convenience script for Windows PowerShell that sets session-only environment variables and starts the app using the project's `.venv-py311` virtualenv. Run it from the repo root: `./start-local.ps1`.

If port 8000 is already in use, `scripts/start_local.ps1` will try 8000 and then fall back to ports 8001..8100 automatically and start the app using `.venv-py311\Scripts\python.exe` when available.

Also included: `data/api_key.secret.example` as an example file the app will read for the API key if env vars are not present.

### Operational endpoints

The application now exposes several operational/observability endpoints:

- `GET /health` or `/healthz` – Basic liveness (always returns 200 if process is running)
- `GET /status` – Returns JSON with `{"status": "running", "version": <app_version>}`
- `GET /ready` – Readiness probe that verifies datastore connectivity and returns uptime seconds. Returns 503 if the database layer is not ready.
- `GET /metrics` – Prometheus metrics (request count & latency histogram) if `prometheus_client` is installed. If not installed, a minimal text payload is still served with HTTP 200 to ensure consistent observability.
- `GET /status/details` – Extended status with runtime toggles:
   - `strict_auth_transactions`: boolean reflecting STRICT_AUTH_TRANSACTIONS
   - `rate_limit_enabled`: boolean reflecting ENABLE_RATE_LIMIT
   - `metrics_mode`: `prometheus` when Prometheus is available, otherwise `fallback`
   - `request_id_enabled`: always `true` in this build
   - `request_id_header`: currently `X-Request-ID`

Additionally, responses include lightweight diagnostics headers:

- `Server-Timing`: includes `app;dur=<ms>` for request duration
- `X-Response-Time`: human-friendly duration string like `12.34ms`
- When rate limiting is enabled: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`, and `Retry-After` on 429 responses

Logging is structured and can emit JSON when `LOG_FORMAT=json` is set in the environment. This improves ingestion into log aggregation systems.

### Request correlation (X-Request-ID)

Every HTTP response now includes an `X-Request-ID` header. If the client supplies
`X-Request-ID` on the incoming request, that value is echoed back; otherwise a
UUID4 is generated. The request id is also attached to `request.state.request_id`
for use by loggers and handlers. This enables end-to-end correlation across load
balancers, the app, and external systems.

### Response timing & rate limit headers

The app emits standard timing and rate limit headers to help clients and SREs:

- `Server-Timing: app;dur=<ms>` and `X-Response-Time: <ms>ms` on all responses
- If `ENABLE_RATE_LIMIT=true`:
   - `X-RateLimit-Limit`: burst capacity
   - `X-RateLimit-Remaining`: remaining tokens at time of response
   - `X-RateLimit-Reset`: coarse seconds until bucket is replenished
   - `Retry-After`: present on 429 responses

### Auth requirement toggle for transactions

By default, for backward compatibility with legacy tests and sample clients, the `POST /transactions` endpoint accepts unauthenticated requests. You can enable a stricter mode that requires authentication and returns HTTP 401 for anonymous writes by setting an environment toggle:

Environment variable:

```
STRICT_AUTH_TRANSACTIONS=1
```

When this is set to `1`, anonymous `POST /transactions` requests will be rejected with `{"detail": "Login required"}` (or `Not authenticated`). This mode is designed for production-like environments, while keeping defaults relaxed for existing demos/tests.

Tip: In pytest, prefer isolating this flag per-test to avoid cross-test leakage. See the isolated DB testing note below.

### Isolated DB testing pattern (pytest)

Some tests in this repo use an isolated SQLite database per-test to avoid cross-test contamination and to exercise the canonical storage path. The typical pattern is:

1. Create a temporary file path for a SQLite DB
2. Set `DATABASE_URL=sqlite:///absolute/path/to/tmp.db` in `os.environ`
3. Call `from app import store; store.init_db()` to initialize schema
4. Construct an `AsyncClient` with `ASGITransport(app=app)` and run requests
5. Clean up env vars and delete the temp file at the end of the test

This ensures tests don't mutate a shared session DB and remain deterministic.

### Optional Rate Limiting

An in-memory token bucket limiter can be enabled for quick protection:

Environment variables:
- `ENABLE_RATE_LIMIT=true` – Activate limiter.
- `RATE_LIMIT_CAPACITY` (default 60) – Burst size.
- `RATE_LIMIT_PER_MINUTE` (default 120) – Sustained rate.

This scaffold is per-process only; for real production use a distributed backend (e.g. Redis + `starlette-limiter`).

### CSP Nonce (Report-Only Rollout)

You can enable a per-request CSP nonce to harden script/style execution:

Environment variables:

- `CSP_NONCE_ENABLED=true` – Turn on nonce generation and injection.
- `CSP_REPORT_ONLY=true` (default) – Emit `Content-Security-Policy-Report-Only` instead of enforcing.
- `CSP_BASE_POLICY="default-src 'self'"` – Base policy; nonce rules for `script-src` & `style-src` are appended automatically.

Violation reports (browsers that support reporting) can be POSTed to `/csp/report`; they are currently logged (structured) for analysis. Once the policy is tuned in report-only mode you can set `CSP_REPORT_ONLY=false` to enforce.

### Coverage & Security Scans

Core CI now generates a `coverage.xml` artifact and runs a vulnerability scan using `pip-audit` (non-blocking). To run locally:

```powershell
python -m pip install coverage pip-audit
coverage run -m pytest -q
coverage report -m
pip-audit -r requirements.txt
```

### Production Readiness Script

Before deploying, execute:

```powershell
python scripts/check_prod_readiness.py
```

It validates presence of required environment variables, weak secrets, port usage, and highlights recommended improvements (e.g. moving off SQLite). Exit code 1 indicates a hard failure.


To set up `pre-commit` locally and run the import-safety check before commits:

```powershell
python -m pip install pre-commit
pre-commit install
pre-commit run --all-files
```

### PostgreSQL (Optional) & Migrations

The application now supports running on PostgreSQL. A `db` service was added to
`docker-compose.yml` along with an Alembic migration scaffold.

Quick start with Docker Compose (app + Postgres + Redis):

```powershell
docker compose up --build
```

By default the compose file sets:

- `DATABASE_URL=postgresql+psycopg://klerno:klerno@db:5432/klerno`
- `DB_CONNECT_RETRIES=10` with exponential backoff for startup races

To generate / apply migrations locally:

```powershell
python -m pip install alembic psycopg[binary]
# Create a new revision (example)
alembic revision -m "add new table" --autogenerate
# Apply migrations
alembic upgrade head
```

Initial revision `0001_initial_core_tables` creates minimal `users` and
`transactions` tables. The legacy `store.py` still auto-manages columns for
SQLite / compatibility; over time these should migrate into explicit Alembic
revisions. When `DATABASE_URL` points to Postgres and `psycopg` is available the
runtime automatically uses Postgres connections.

Fallback: If Postgres is unavailable the app will continue to work with SQLite.
