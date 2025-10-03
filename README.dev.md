# Development quickstart

This file explains the fastest way to run the app locally for development and debugging.

Prerequisites
- Python 3.11 venv (or compatible)
- Install project deps into a venv: pip install -r requirements.txt

Seed the local DB (creates dev & admin users)

Run from the project root (venv active):

```powershell
.\.venv-py311\Scripts\Activate.ps1  # or your venv activate
python .\tools\seed_local_db.py
```

Start the dev server

The repo provides a safe helper that sets dev-friendly env vars and chooses a free port if 8000 is busy.

```powershell
# Start in the foreground (useful for logs):
$env:LOCAL_PORT='8000'
python .\scripts\run_local.py

# Or start it in background from PowerShell:
$env:LOCAL_PORT='8000'
Start-Process -FilePath .\.venv-py311\Scripts\python.exe -ArgumentList 'scripts/run_local.py'
```

Probe login and get a token

A probe helper will try common ports and endpoints and print the access/refresh token on success.

```powershell
python .\tools\login_probe.py
```

Save tokens locally or to the OS keyring

The probe supports saving discovered tokens for convenience:

```powershell
# Save tokens to a local file (.run/dev_tokens.json)
python .\tools\login_probe.py --save-token

# Store tokens in the OS keyring instead (if available)
python .\tools\login_probe.py --save-token --use-keyring
```

Notes:
- Saved tokens are written to `.run/dev_tokens.json` by default and include `saved_at` and `access_token_expiry` fields.
- `.run/` is gitignored by the repository; do not commit token files.

Useful diagnostics

- `tools/diagnose_logging_and_routes.py` — inspects structlog configuration and lists registered FastAPI routes. Use this if startup fails or a route is missing.
- `tools/preview_smoke_test.py` — small in-process smoke test for operational endpoints using TestClient.

CI suggestions

- The project now runs a startup diagnostic early in CI to catch import-time issues (see `.github/workflows/core-ci.yml`).

Security

- The seeded users and tokens are for local development only. Do not commit tokens or .env files containing secrets.

---

Quick dev flow (all-in-one)

```powershell
# activate venv
. .\.venv-py311\Scripts\Activate.ps1
# seed DB
python .\tools\seed_local_db.py
# start dev server (foreground)
python .\scripts\run_local.py
# in another shell, probe login and save token for convenience
python .\tools\login_probe.py --save-token
```

Run the full local smoke flow (seeds DB, starts server, probes login, runs smoke checks)

```powershell
# single command to run the entire local smoke flow (Windows PowerShell)
python .\tools\run_local_smoke.py
```

Compatibility paths and behaviors

- Auth forwarders
  - POST /auth/register forwards to the API signup and returns `{ email, id }` while preserving Set-Cookie.
  - POST /auth/login accepts JSON or form data and returns `{ ok, access_token, token_type }` and sets the session cookie.
  - Prefer calling `/auth/signup/api` and `/auth/login/api` directly from programmatic clients; the forwarders exist for tests and legacy callers.

- Transactions and compliance tags
  - When the legacy `transactions` table exists, POST /transactions writes there and, for high-value amounts (>= 50,000), inserts a `HIGH_AMOUNT` tag into `compliance_tags`.
  - When the canonical `txs` store is used (no legacy `transactions` table), we still insert a `HIGH_AMOUNT` row into `compliance_tags` so `/transactions/{id}/compliance-tags` returns data consistently in tests.

- XRPL compatibility
  - GET /integrations/xrpl/fetch always returns an object with an `items` array (and optional `count`). If the underlying client returns a list, it will be wrapped.

- Audit logging (dev vs test)
  - In dev, audit events log to console at INFO and to `logs/audit.log`.
  - In tests, console output is reduced (WARNING level) and file output is disabled by default; set `DISABLE_AUDIT_FILE=0` to force file logging if needed.

Release notes template

See `RELEASE_NOTES_TEMPLATE.md` for a small release-notes stub you can use when cutting tags.

Runbook

For deploy/run steps and rollback instructions see `docs/DEPLOY_RUNBOOK.md`.

SMOKE alert webhook (optional)

The scheduled nightly smoke workflow can post a concise alert to an incoming webhook when the smoke test fails. To enable this, add a repository secret named `SMOKE_ALERT_WEBHOOK` with the webhook URL.

Common options:
- Slack: create an Incoming Webhook in your workspace and use the webhook URL as the secret value.
- Microsoft Teams: use an Incoming Webhook connector on a channel and use that URL.

Payload example (what the workflow posts):

```json
{

  "text": "Nightly smoke FAILED for owner/repo (run 123456)\nhttps://github.com/owner/repo/actions/runs/123456\n\n<truncated smoke output>"
}
```

Notes:
- The workflow truncates the smoke output to ~3500 characters to keep alerts compact.
- If `SMOKE_ALERT_WEBHOOK` is not present, the workflow skips the webhook step silently.

Optional: mention and HMAC signing

You can customize the webhook alert behavior with two optional repository secrets:

- `SMOKE_ALERT_MENTION` — a short text (for example `@dev-team` or `<!subteam^ID>`) that will be prepended to the message. Useful when your webhook supports mentions.
- `SMOKE_ALERT_SECRET` — an HMAC key used to sign payloads. When present the workflow sets an `X-Signature` header with the hex-encoded HMAC-SHA256 of the JSON body. Configure your receiver to verify this signature if you want to ensure alerts only come from CI.

Advanced: standardized signature header and retry

The workflow now uses the `X-Hub-Signature-256` header with the value in the format `sha256=<hex>` when `SMOKE_ALERT_SECRET` is configured. This matches the common convention used by many webhook receivers (for example GitHub's webhooks). The workflow will also retry webhook posts up to 3 times with exponential backoff for better reliability.

Issue triage automation

Two more optional secrets help with triage when issues are created automatically:

- `SMOKE_ALERT_ISSUE_LABELS` — comma-separated labels to add to the created issue (for example `smoke,automated-alert`).
- `SMOKE_ALERT_ISSUE_ASSIGNEES` — comma-separated usernames to assign to the created issue.

If these are set, the workflow will populate the labels and assignees when creating the issue on failure.

Signature verification examples

If you set `SMOKE_ALERT_SECRET`, the workflow sends `X-Hub-Signature-256: sha256=<hex>`.

Python (Flask/any WSGI) example to verify:

```python
import hmac, hashlib
from flask import request, abort

def verify(req_body: bytes, signature_header: str, secret: str) -> bool:
  if not signature_header:
    return False
  if not signature_header.startswith('sha256='):
    return False
  sig = signature_header.split('=', 1)[1]
  mac = hmac.new(secret.encode('utf8'), req_body, hashlib.sha256).hexdigest()
  return hmac.compare_digest(mac, sig)

@app.route('/webhook', methods=['POST'])
def webhook():
  body = request.get_data()
  sig = request.headers.get('X-Hub-Signature-256', '')
  if not verify(body, sig, 'your-secret'):
    abort(401)
  # handle payload...
```

Node (Express) example:

```js
const crypto = require('crypto');
function verify(req, secret) {
  const sig = (req.get('X-Hub-Signature-256') || '').replace(/^sha256=/, '');
  const h = crypto.createHmac('sha256', secret).update(req.rawBody || '').digest('hex');
  return crypto.timingSafeEqual(Buffer.from(h, 'hex'), Buffer.from(sig, 'hex'));
}
```

Example: set `SMOKE_ALERT_MENTION` to `@dev-team` and `SMOKE_ALERT_SECRET` to a 32+ character random string in repository Secrets.
