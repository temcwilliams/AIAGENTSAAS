# Security review — 2026-11-13

This review combined an independent local red-team code review, adversarial API tests using disposable accounts/databases, and published dependency advisory checks. It did not attack production customer data. Strix tools repeatedly requested authentication after reconnection; no Strix scan ran and no credits were spent.

## Findings and changes

| Finding | Change | Verification |
|---|---|---|
| Frontend read the entire body before its character limit; backend had no byte limit before JSON parsing | Bound both layers to 64,000 bytes while reading; reject declared oversized bodies early; preserve valid UTF-8 | Declared, chunked, multibyte, exact-boundary and cancellation tests |
| Random email targets bypassed per-email login throttling; concurrent Argon2 work could exhaust memory | Database-backed global login budget (30/minute by default), plus one active hash/verification per worker and retryable 429 | Random-target spray and simultaneous hash/verification tests; existing authentication tests |
| Synchronous DB locks in async chat handler could block the event loop; waiting mutations could exhaust connection/worker pools during inference | Run synchronous transactions in FastAPI workers; PostgreSQL FOR UPDATE NOWAIT across chat/handoff/reply mutations; contention rolls back and returns 409 with Retry-After | Concurrent health check during simulated blocking; real PostgreSQL SQL compilation; simulated driver lock errors across five mutation routes |
| Client could create unbounded empty conversations without sending chat messages | Shared per-business creation budget, default 120/hour, after tenant/resource validation | Cross-user/agent quota, denied inserts, foreign-resource rejection and independent-tenant tests |
| Published dependency advisories in Next.js, its image/CSS dependencies, Starlette, pytest and pip | Next.js 15.5.29; patched PostCSS/sharp overrides and lockfile; FastAPI 0.162.7 / Starlette 1.10.0; pytest 9.0.3; pip 26.3 in container builds and Linux setup | npm audit and pip-audit after upgrades; production build; backend regression suite; SQLite migration round trip |

Package advisory severity does not by itself establish an exploitable application path: several advisories concern unused features or Windows. Affected packages were nevertheless updated. Audits report published advisories known at check time, not proof that every dependency is vulnerability-free.

## Scope and limits

- Existing tenant authorization, role overposting resistance, forged sessions, session revocation, owner signup, and provider-failure behavior remain covered by tests.
- PostgreSQL lock behavior was checked with compiled PostgreSQL SQL and simulated driver errors, not a live PostgreSQL stress test. SQLite does not implement PostgreSQL row locks.
- No real model calls, user password resets, email sends, new paid resources, or credential changes were needed.
- Request and login budgets bound resource use; they do not guarantee availability under distributed attacks. The global budget can temporarily deny legitimate logins during abuse. Password concurrency is per worker, so deployment worker counts must fit available memory.
- Conversation throttling is not a lifetime storage quota. Retention/deletion, backups/restore drills, monitoring, email verification, and account recovery remain outstanding work documented in PROGRESS.md and the milestone plan.
- This review does not replace a comprehensive external penetration test. Live deployment status and exact test counts are maintained in [PROGRESS.md](../PROGRESS.md).

## Reproduce locally

```sh
cd backend
../.venv/bin/python -m pytest -q
cd ../frontend
npm ci
node tests/request-body.test.mjs
npm run build
npm run typecheck
npm audit
```

Run backend tests from `backend/` as described in the main README. For Python dependency advisory checks, install the free `pip-audit` tool in a development virtual environment and run `pip-audit`; audits require access to public advisory services. Test fixtures and model responses are disposable/mocked. Do not point automated exploit tests at production accounts.

## 2026-11-16 follow-up — owner-approved account access

At the user’s request, public signup and browser owner setup were retired. Accounts are now provisioned by the platform administrator after email contact. The registration endpoint unconditionally rejects requests before database access, request schema validation, or password hashing; old owner codes cannot reopen it. Existing data and sign-in are preserved, and initial-owner bootstrap for fresh installations remains an offline operator action.

An independent local red-team reviewer found **no bypass** in three added regression tests. Checks exercised canonical/encoded/trailing paths across text, form and multipart bodies; alternate methods and method overrides; configured matching legacy owner codes while authenticated as admin; client role/tenant/header spoofing; account field overposting; session injection; and newly provisioned client tenant/admin isolation. A separate seven-case access suite verifies disabled registration without an administrator/database access and successful admin-provisioned client sign-in. Full backend suite: **68 passed** with one upstream TestClient deprecation warning.

Live checks after the Free Render deployment verified the email-only access interface, scrubbed legacy fragments, disabled signup (403), protected APIs (401), request byte limits (413), health (200), and PWA/offline behavior. No production accounts were created or modified and no email was sent. These tests do not establish universal vulnerability absence or replace a comprehensive external assessment. Strix is excluded from the active checklist at the user’s request; no Strix tools or paid scans were used for this review.
