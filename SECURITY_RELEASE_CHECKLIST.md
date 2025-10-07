# Security Release Checklist

This checklist captures the minimal security & privacy steps to complete before a public production release.
Tailor items to your organization's policy and regulatory needs.

Minimum required items (pre-release):

- Secrets & keys
  - [ ] Rotate any dev/test secrets used in CI or local dev (e.g., JWT_SECRET, API keys).
  - [ ] Ensure no plaintext secrets are stored in the repository (.env files, data/api_key.secret).
  - [ ] Confirm CI environment variables are stored in the secrets store; do not echo them in logs.

- Authentication & session
  - [ ] Enforce strong JWT_SECRET with length >= 32 and high entropy.
  - [ ] Ensure session cookies set Secure and HttpOnly flags and SameSite=strict where appropriate.
  - [ ] Verify account lockouts and rate-limiting for auth endpoints.

- Transport & network
  - [ ] Require TLS in front of the application; do not serve tokens over plaintext.
  - [ ] Harden CORS to only allow known origins for production.

- Data protection & storage
  - [ ] Ensure database credentials are not checked into source control.
  - [ ] Encrypt sensitive at-rest data where required by policy.

- Dependencies & supply chain
  - [ ] Run `pip-audit` and resolve any critical findings.
  - [ ] Generate and review SBOM (CycloneDX) and confirm licenses and supply chain provenance.

- Infrastructure & ops
  - [ ] Configure centralized logging with PII redaction.
  - [ ] Configure metrics & alerting for high-error-rate and auth anomalies.
  - [ ] Verify backups and restore procedures for the production database.

- Testing & hardening
  - [ ] Run an automated security scan (Bandit, Snyk, or equivalent).
  - [ ] Conduct a vulnerability scan and fix high/critical issues.
  - [ ] Perform a pen-test or a threat-model review for public releases.

- Release controls
  - [ ] Ensure CI gates (lint, tests, readiness checks) pass before merge.
  - [ ] Confirm artifact signing and integrity check procedures for release assets.

Notes & follow-ups:
- Consider adding an automated job that fails the release if `scripts/check_prod_readiness.py` returns non-zero.
- Consider rotating deployment keys and adding CI step to prevent accidental artifact uploads containing secrets.
