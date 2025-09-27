# Security Overview

This document summarizes the current security posture of the Klerno Labs application and recommended next steps for production readiness.

## Implemented Controls

- Hardened session cookies (`SameSite=Strict`, `Secure` outside development)
- Secret validation at startup (rejects weak JWT secret in non-dev environments)
- Minimal Content Security Policy (`default-src 'self'`)
- Structured logging (supports JSON via `LOG_FORMAT=json`)
- Readiness (`/ready`) vs liveness (`/health`) separation
- Optional Prometheus metrics (`/metrics`) for observability
- Non-root Docker user (`appuser`)
- Basic security headers (X-Content-Type-Options, X-Frame-Options, X-XSS-Protection, HSTS)

## Recommended Immediate Enhancements

1. **Rate Limiting**: Integrate a limiter (e.g. `slowapi` or `starlette-limiter`) for auth & sensitive endpoints.
2. **CSP Tightening**: Add explicit script/style sources; consider nonce-based CSP if dynamic content required.
3. **Dependency Audit**: Add `pip-audit` or `safety` to CI; schedule weekly runs.
4. **Secrets Management**: Use a vault or cloud secret manager instead of environment variables for production.
5. **Database Hardening**: Migrate from SQLite to PostgreSQL for concurrency and durability.
6. **Transport Security**: Enforce TLS termination at edge (nginx / load balancer) with automatic certificate rotation.
7. **JWT Improvements**: Short-lived access tokens (default 15m) and long-lived refresh tokens (default 7d) are now implemented. Refresh tokens are single-use and rotated on each refresh. Revoked/used tokens are tracked until expiry. Redis is used for distributed storage if enabled, otherwise in-memory fallback is used.
8. **Input Sanitization**: Add HTML escaping validation for any user-submitted rich text (if added later).
9. **Audit Logging**: Centralize security events (auth, privilege changes) with integrity protection.
10. **Backups & DR**: Automated encrypted backups of database with restore drills.

## Defense in Depth Roadmap

| Phase | Item | Description |
|-------|------|-------------|
| Short | Rate limiting | Throttle brute force & abuse |
| Short | Dependency scanning | Automated CVE surfacing |
| Short | Secret rotation policy | Doc + script to rotate JWT secret |
| Medium | DB migration | PostgreSQL with migrations tooling |
| Medium | Advanced CSP | Nonce/sha256 hashed inline scripts |
| Medium | Security testing | Add DAST and SAST (Bandit) |
| Long | Zero trust endpoints | mTLS or signed requests for internal APIs |
| Long | Continuous compliance | Map controls to SOC2 / ISO27001 |

## Operational Checks

Use `scripts/check_prod_readiness.py` to perform pre-deploy sanity validation (env vars, weak secrets, migrations placeholder).

## Reporting Vulnerabilities

Please open a private security advisory or email the maintainers. Avoid filing public issues for unpatched vulnerabilities.
