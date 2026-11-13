> Historical two-service instructions: use `docs/optional-render-two-services.yaml` for this older path. The current root `render.yaml` follows [render-pwa.md](render-pwa.md) instead.

> Optional legacy cloud deployment. This path may incur charges. For the free default, use the root README and compose.yaml. Set `AI_PROVIDER=cloud` and `OPENAI_BASE_URL=https://api.openai.com/v1` explicitly when using a paid provider; the current application defaults to local Ollama.

# Agent Meadow · Milestone 1

A hybrid AI service workspace: the platform administrator manages businesses and agent configurations; client users see only their business's agents, conversations, leads, and usage. Includes a Next.js/TypeScript/Tailwind dashboard and FastAPI REST API backed by Neon PostgreSQL. No infrastructure is provisioned by this repository.

## Local setup

Requirements: Python 3.12+, Node 22+, and a PostgreSQL database (Neon or local).

```sh
python -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local
```

Edit `backend/.env`: supply your database URLs. Use `postgresql+psycopg://` URLs; URL-encode special characters in credentials. Neon connections must include `sslmode=require` (or `verify-full` with trusted CA configuration). Use pooled `DATABASE_URL` for runtime and direct `DATABASE_URL_UNPOOLED` for Alembic. Use a dedicated development Neon branch rather than production data. Keep `ENVIRONMENT=development` locally; both APP_ORIGIN settings must match the exact browser origin, without a trailing slash.

```sh
cd backend
../.venv/bin/alembic upgrade head
../.venv/bin/python -m app.bootstrap
../.venv/bin/uvicorn app.main:app --reload --port 8000
```

In a second terminal:

```sh
cd frontend
npm ci
npm run dev
```

Open http://localhost:3000. Sign in as the bootstrapped administrator, open Business settings to create a business and client accounts, and configure an agent under Agents. Clients use the same sign-in page. Agent model IDs must be supported by your configured provider.

## External credentials and approval

You must supply Neon database credentials and an OpenAI-compatible provider API key through local environment files or Render secrets, never chat or source control. `OPENAI_BASE_URL` is operator-controlled, shared across agents, and must support `/chat/completions` with standard `usage.prompt_tokens` and `usage.completion_tokens`. No mock fallback is used. Missing credentials return 503; malformed or failed upstream responses return 502 without saving a partial turn. Chat sends message content and system instructions to that provider and may incur charges. Tests mock this boundary and make no paid AI calls.

Creating Neon resources, selecting Render plans, applying `render.yaml`, running production migrations, or sending live AI test messages requires your approval. None has been done automatically. Package installation, local tests, and builds do not provision application services.

## Tests and build

```sh
cd backend
../.venv/bin/python -m pytest -q
cd ../frontend
npm run build
npm run typecheck
```

Tests cover authentication, logout revocation, origin protection, login throttling, role permissions, cross-business list/resource access, composite foreign keys, lead routes, disabled agents, successful chat persistence and provider-failure rollback. Tests use isolated SQLite databases; run migrations and integration checks on a disposable PostgreSQL/Neon branch before deployment to validate PostgreSQL-specific locking and schema behavior. `/docs` exposes the generated OpenAPI API reference.

## Render deployment (manual, after approval)

1. Review pricing and choose service sizes in Render before applying the Blueprint. `render.yaml` deliberately disables automatic deployment and preview environments. Its two services use your external Neon database; it does not create a Render database.
2. Push the repository to your Git host and create a Render Blueprint. Set `DATABASE_URL` (pooled) and `DATABASE_URL_UNPOOLED` (direct) as backend secrets; use a production Neon branch and TLS. Set `ENVIRONMENT=production`.
3. Set `APP_ORIGIN` on **both** services to the final frontend HTTPS origin. Set frontend `BACKEND_URL` to the backend HTTPS service URL. Set backend `OPENAI_API_KEY` and optionally `OPENAI_BASE_URL`. These variables are server-side only. `sync: false` prompts on initial Blueprint setup; update subsequent secrets in Render's environment settings.
4. The backend pre-deploy command runs Alembic. Back up data and review migrations first. Choose a Render service plan supporting pre-deploy commands, or run `alembic upgrade head` manually with the direct URL before starting the API. Bootstrap the initial admin once using `python -m app.bootstrap` from an interactive Render shell or a trusted local terminal connected to the target database.
5. Deploy API and frontend manually. Verify `/health`, sign-in, admin business creation, client isolation, and one approved live chat request. Verify token totals. Configure custom domains before finalizing APP_ORIGIN. Never set development mode in production.

## Security model and limits

- Argon2id password hashes; random 384-bit session tokens stored only as SHA-256 digests; 12-hour expiry; HTTP-only, SameSite=Strict cookies and production Secure cookies; logout deletes the server session.
- No public signup or user-supplied role assignment. Admin bootstrap is an offline operator action. Business access comes from the authenticated database user, never browser role claims. Every business route checks access; resource queries also filter by business ID. Composite foreign keys reject cross-business agent/conversation/message/usage references. Admins have intentional cross-tenant access.
- All writes require exact `Origin`; non-browser REST clients must set it too. The Next proxy only forwards approved route families and never exposes AI/database credentials. API has no cross-origin browser access enabled. React escapes message text; HTML is not rendered from agents.
- Account login attempts are persisted and throttled (10 per 15-minute window). This baseline is not a distributed abuse-control system: put a managed edge rate limiter in front of public services for launch, and set appropriate per-business chat limits before broad access. The database counter uses an atomic upsert across workers; add IP-based protection at the edge for high traffic.
- PostgreSQL row locks serialize chat turns per conversation; bounded context and output tokens limit individual requests. Upstream calls hold a database transaction for up to 60 seconds. No automatic provider retries, avoiding accidental duplicate charges. Provider success followed by DB/network failure can still create unrecorded provider usage; reconcile provider invoices before billing customers.
- No automatic lead extraction: leads are manually entered by the administrator and visible to clients. Performance currently means request, conversation, lead, and token counts, not response-quality or conversion scoring. Lists are capped at 100; conversation and business lists accept `offset`; message history is capped at 200 and AI context uses the latest 40 messages.
- MFA, email verification, email-based password recovery, user lifecycle management, automated retention, audit trails, and token/spend quotas are future hardening, not implemented in this milestone. Share initial credentials securely; do not onboard broad public access until these policies are chosen.

## Modular architecture

`backend/app/security.py` owns identity and authorization; `models.py` owns persistence; `ai.py` isolates the provider adapter; `schemas.py` validates input; `main.py` defines REST routes. `migrations/versions/initial_schema.py` freezes the initial schema independently from live models. Add explicit Alembic revisions for future changes (do not edit the applied initial migration). The UI and same-origin API proxy live under `frontend/src/app`.

Future billing should consume immutable usage records and reconcile provider usage; integrations should use tenant-scoped service credentials and durable background jobs. A future 3D agent floor can consume the same business/agent APIs plus a separate presence/event layer. Do not overload identity or conversation tables with billing, connector secrets, or visualization state.

## Production-readiness follow-up

Run `alembic upgrade head` to apply revision `0002` before starting the updated API. It adds a database table for atomic rate-limit reservations. The original migration remains unchanged.

Both admin and client users now have an **Account security** page. `POST /auth/password` requires the current password and a different new password of 12–128 characters; success revokes every session and signs the user out. Password-change attempts are limited to five per 15 minutes. `POST /auth/logout-all` revokes every session for the authenticated user. Neither action affects other users. Password changes and login acquire the same PostgreSQL user-row lock to serialize credential updates with sign-in.

`CHAT_REQUESTS_PER_HOUR` defaults to **60 per business**, shared by all its users, agents, and conversations, including admin tests. The window begins on the first attempt and resets one hour later. Reservation happens before the provider call and survives provider errors, missing credentials, and process interruption. Requests rejected for tenant ownership, nonexistent resources, or disabled agents do not consume an allowance. Invalid or oversized conversation context can consume an allowance. A rejected request returns 429 and a conservative `Retry-After` value. This caps request attempts; it is not a currency budget or token quota. Limits are atomic across workers. Expired buckets reset on reuse; a retention cleanup task remains future work.

The frontend clears cached workspace data when switching business or signing out and ignores late workspace refresh results from a previously selected business.
