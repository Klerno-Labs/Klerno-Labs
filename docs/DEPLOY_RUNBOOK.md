Deploy runbook (one-line + quick checks)

Purpose
-------
This runbook is a minimal set of commands and checks to deploy the application
for a quick validation or smoke-test in a staging environment.

One-line deploy (container)
---------------------------
Build and run locally (example):

```bash
docker build -t klerno-app .
docker run --rm -e APP_ENV=production -e JWT_SECRET='your-very-strong-secret' -p 8000:8000 klerno-app
```

Quick smoke/tests (after deployment)
-----------------------------------
- Run readiness check in container or from host:

```bash
python scripts/check_prod_readiness.py
```

- Execute the release smoke workflow locally (if you have tokens saved):

```bash
python tools/prod_smoke_test.py --url http://127.0.0.1:8000 --token-file .run/dev_tokens.json
```

Rollback
--------
- If the deployment fails, re-run the previous image tag (if available):

```bash
docker run --rm -e APP_ENV=production -e JWT_SECRET='your-very-strong-secret' -p 8000:8000 klerno-app:previous
```

Notes
-----
- Make sure sensitive secrets are supplied via your orchestrator/secret manager in production.
- The readiness script is intentionally cautious and will return non-zero if required production settings are missing.
