# Klerno Labs Roadmap

This roadmap captures the next staged improvements following the initial CI, security, and observability hardening PR.

## Guiding Principles

- Small, reviewable PRs (target <500 LOC diff)
- Additive, feature-flagged where risk exists
- Ratchet quality (coverage, security scanning) incrementally
- Fast feedback: metrics + readiness first, deeper refactors second

## Phase 1 (Immediate / Short Term)

| Item | Goal | Acceptance Criteria |
|------|------|---------------------|
| Coverage ratchet (DONE) | Raise baseline coverage to 25% | CI fails <25%; README reflects plan |
| CodeQL (DONE) | Baseline static analysis | CodeQL workflow runs on PRs & weekly schedule |
| Weekly dependency audit (DONE) | Scheduled visibility into CVEs | Workflow artifacts with JSON reports |
| SBOM generation (DONE) | Supply chain transparency | `sbom.json` artifact uploaded in CI |
| Pre-commit tooling (DONE) | Local consistency & security | `pre-commit run --all-files` passes |

## Phase 2 (Configuration & Modularity)

| Item | Goal | Acceptance Criteria |
|------|------|---------------------|
| Pydantic settings | Centralize env + validation | Weak secret rejected in prod; tests updated |
| Router modularization | Reduce `main.py` size, clarify domains | Routers in `app/routers/`; main orchestrates |
| Repository abstraction | Decouple persistence | Interfaces + SQLite impl; tests using mock repo |

## Phase 3 (Platform Hardening)

| Item | Goal | Acceptance Criteria |
|------|------|---------------------|
| PostgreSQL migration | Production-grade DB path | docker-compose Postgres; Alembic baseline; docs |
| Redis rate limiting | Distributed abuse protection | 429 with X-RateLimit headers; configurable limits |
| CSP nonce rollout | Stronger content security | Report-Only CSP with nonce; violation logging |
| Audit logging | Security event traceability | Structured audit events for login, role change |

## Phase 4 (Auth & Session Evolution)

| Item | Goal | Acceptance Criteria |
|------|------|---------------------|
| JWT rotation & refresh | Short-lived access tokens | Refresh endpoint; revocation list; tests cover edge cases |
| Secrets management prep | External secret lifecycle | Design doc + interface; environment injection guidelines |

## Phase 5 (Observability & Scale)

| Item | Goal | Acceptance Criteria |
|------|------|---------------------|
| OpenTelemetry tracing | Cross-request visibility | Spans emitted when OTEL vars set; silent otherwise |
| Performance baseline | Quantify latency & throughput | Basic k6/Locust profile & stored results |

## Phase 6 (Security & Supply Chain Advanced)

| Item | Goal | Acceptance Criteria |
|------|------|---------------------|
| Coverage ratchet to 40% | Improve test depth | CI threshold = 40% (later PR) |
| CodeQL query tuning | Reduce noise | Custom query pack; lower false positives |
| Automated SBOM diff | Detect dependency drift | CI job highlights new packages vs prior main |

## Issue Templates (Copy/Paste)

### feat(config): pydantic settings centralization

Objective: Replace scattered env access with validated `Settings`.

Acceptance: App fails fast on weak secret in prod; tests updated; documentation updated.

### refactor(routers): modularize main

Objective: Extract domain routes into `app/routers/` to reduce complexity.

Acceptance: `app/main.py` <300 lines; all tests pass.

### feat(db): PostgreSQL migration scaffold

Objective: Introduce Postgres with Alembic baseline; keep SQLite fallback.

Acceptance: `docker-compose up db` provides Postgres; migration generates tables; readiness passes.

### feat(rate-limit): Redis-backed limiter

Objective: Replace in-memory limiter with Redis backend for per-IP + per-identity quotas.

Acceptance: Exceeding quota returns 429 with Retry-After and X-RateLimit headers.

### feat(csp): nonce-based CSP (report-only)

Objective: Protect against XSS with CSP nonce rollout.

Acceptance: Pages render with nonce; report-only header present; violation logs accessible.

### feat(auth): JWT rotation & refresh flow

Objective: Increase session security with short-lived access + refresh tokens.

Acceptance: Access token expires; refresh issues new token; revoked token rejected.

### feat(tracing): OpenTelemetry integration

Objective: Enable distributed tracing optionally.

Acceptance: When OTEL env vars set, spans appear; otherwise negligible overhead.

### feat(audit): structured audit log

Objective: Record critical security events with stable schema.

Acceptance: JSON entries for login success/failure, password change, role updates.

## Ratchet Plan

- Current threshold: 25%
- Target increments: 25% → 35% → 50% → 65%+

Each increase after adding meaningful tests (repositories, auth edge cases, readiness failure paths).

## Notes

- Keep each PR atomic; avoid bundling multiple roadmap items.
- Use feature flags/env toggles for riskier additions (tracing, Redis limiter) to preserve safe rollback.

---

Maintained alongside SECURITY.md and DESIGN_CRITIQUE.md.
