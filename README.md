# Agent Meadow · PWA and free local edition

[Project progress](PROGRESS.md) — current deployment, completed work, verification, blockers, and next steps.

A multi-tenant AI agent SaaS starter with admin/client roles, business dashboards, configurable agents, test chat, leads, conversation history, token tracking, and account-security controls. It now runs on **free, open-source software with no required cloud account, paid API, or subscription**.

| Component | Free software |
|---|---|
| Dashboard | Next.js, TypeScript, React, Tailwind CSS |
| API | Python, FastAPI |
| Database | Self-hosted PostgreSQL |
| AI inference | Ollama, running locally |
| Starter model | `qwen2.5:1.5b` (Apache 2.0 weights) |
| Containers | Podman + a Compose provider |

Hosting on your own computer avoids cloud service fees. Hardware, electricity, internet access, and backups remain your responsibility. This is not a promise of free public cloud hosting or unlimited compute. Local model quality and speed depend on your hardware; the small starter model prioritizes modest resource needs.

## Free setup with Podman

Install Python 3 (for the one-time configuration generator), [Podman](https://podman.io/), and a Compose provider such as `podman-compose`. On macOS/Windows, start a Podman machine first. Allow several GB of disk space for images and model weights; 8 GB RAM is a practical starting point for the complete small-model stack, not a guaranteed minimum. CPU inference is supported; no GPU is required.

From the project root:

```sh
python3 scripts/init-local.py
podman compose up --build -d
podman compose exec ollama ollama pull qwen2.5:1.5b
podman compose exec api python -m app.bootstrap
```

The generator writes a random local database password into a private, gitignored `.env`; it refuses to overwrite an existing file. The model pull downloads weights but does not use a paid AI API. Admin bootstrap asks for your email and password interactively. Wait for the API to start before bootstrapping; inspect `podman compose logs migrate api` if startup fails.

Open **http://localhost:3000**. Create a business under Business settings, then create an agent using model ID **`qwen2.5:1.5b`**. You can create client accounts and test chat immediately. Existing agents configured with OpenAI model IDs must be updated to an installed Ollama model ID.

`podman compose` requires a provider supporting health and completed-service dependency conditions. If your provider does not support them, run the stages explicitly:

```sh
podman compose up -d db ollama
# Wait until: podman compose exec db pg_isready -U agent_studio -d agent_studio
podman compose run --rm --no-deps migrate
podman compose up --build -d --no-deps api web
```

Docker Engine + Compose can also run the same files using `docker compose`. Podman is the recommended route when you want to avoid Docker Desktop licensing conditions. No managed hosting is used.

## Operations and data

```sh
podman compose logs -f api
podman compose stop
podman compose up -d
```

Database records and model downloads persist in named volumes. `podman compose down` preserves volumes; **do not add `-v`** unless you intend to delete all data and models. Keep `.env` safe: changing its password alone does not rotate an existing PostgreSQL volume's credentials. Back up PostgreSQL regularly using `pg_dump` and test restoration.

Only the frontend port is published, bound to `127.0.0.1`. PostgreSQL, Ollama, and the API stay on the container network. Local mode uses HTTP and non-Secure cookies for localhost. **Do not expose this configuration directly to the public internet.** Public client access requires an HTTPS reverse proxy, production cookie settings, database TLS, backups, and a machine reachable by your clients. Free software supports self-hosting, but public hosting resources may cost money. Nothing is provisioned or deployed automatically.

## Configuration

The root `.env` configures the container stack. Separate `backend/.env.example` and `frontend/.env.example` files are for running the Python/Node processes directly, without containers.

- `AI_PROVIDER=local` is the new default. It uses Ollama's OpenAI-compatible `/v1/chat/completions` API, needs no API key, and never sends a retained cloud key to the local server.
- Local AI endpoints are restricted to loopback hosts or the private `ollama` hostname. No environment HTTP proxy is used for local requests. Other local server names require an explicit code/configuration review.
- `OPENAI_BASE_URL` is `http://ollama:11434/v1` inside Compose, or `http://127.0.0.1:11434/v1` for native development. Native Ollama must be installed and running separately.
- `APP_ORIGIN` must equal the exact browser origin. If you change the frontend URL, update it consistently.
- `CHAT_REQUESTS_PER_HOUR` defaults to 60 per business across users and agents. Failed provider attempts count. This prevents unbounded requests but is not a token or currency budget.
- `LOGIN_REQUESTS_PER_MINUTE` defaults to 30 globally, shared across workers and email addresses. Per-email limits also apply. Argon2 operations are limited to one per worker; concurrent attempts receive 429 and a retry hint. These bounds protect the small free instance; a sustained attack can still temporarily deny login capacity.
- JSON requests are limited to 64,000 bytes before parsing at both the frontend proxy and backend. Conversation mutations use PostgreSQL nonwaiting row locks: overlapping turns/handoff updates return 409 with a retry hint. Database waits run outside the API event loop.
- `CONVERSATIONS_PER_HOUR` defaults to 120 per business across users and agents, limiting empty-conversation storage abuse. Long-term retention and storage quotas remain future work.
- The database password is randomly generated; no production credentials are hardcoded. Keep environment files out of source control.
- Local inference timeout is 180 seconds; cloud inference remains 60 seconds. Very slow local models may still time out.

For native development, install PostgreSQL and Ollama locally, create a dedicated PostgreSQL database/user with a random password, fill `backend/.env` with its `postgresql+psycopg://` URL, then run:

```sh
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
cd backend
../.venv/bin/alembic upgrade head
../.venv/bin/python -m app.bootstrap
../.venv/bin/uvicorn app.main:app --port 8000
```

In another terminal, copy `frontend/.env.example` to `frontend/.env.local`, then run `npm ci && npm run dev` from `frontend`. Pull the starter model with `ollama pull qwen2.5:1.5b`. Both backend and frontend require the same APP_ORIGIN.

## Tests

```sh
cd backend
../.venv/bin/python -m pytest -q
cd ../frontend
npm ci
npm run build
npm run typecheck
```

The suite tests authentication, session expiry/revocation, password changes and recovery actions, scoped business roles, account disabling, onboarding publication, tenant isolation, composite database constraints, shared request limits, conversation/token persistence, failed-provider rollback, and local/cloud provider adapters. Tests use isolated SQLite databases, an in-memory test mailbox, and mocked AI responses. No paid calls or real email occur. PostgreSQL locking and live Ollama inference require separate integration validation. CI configuration is included under `.github/workflows`.

## Architecture and security

`backend/app/security.py` handles identity and tenant authorization; `limits.py` owns atomic request limits; `ai.py` isolates inference; `models.py` owns persistence; `schemas.py` validates requests; `main.py` exposes REST endpoints. Next.js UI and same-origin API proxy live under `frontend/src/app`. OpenAPI docs are available at `/docs` on the API when accessed within the container network or through native development.

Passwords use Argon2id. Sessions and email action tokens are random values stored only as digests. Public signup and browser owner setup are disabled. Only an authenticated administrator can create businesses and client accounts. Offline admin bootstrap remains available for a new installation without an administrator. All business endpoints enforce tenant authorization and scope resource queries. Admins intentionally manage all businesses. Viewer, Responder, and Manager memberships are checked from the database on every request; composite foreign keys reject mixed-tenant references. Writes require the configured Origin. Password changes and successful recovery revoke every session; “sign out everywhere” is available to clients and admins. PostgreSQL locks serialize chat turns. Alembic migrations run before the container API starts.

Leads are manually recorded by admins; performance metrics are request, conversation, lead, and token counts. MFA, audit trails, automated retention, and per-tenant token budgets remain future work. Billing, integrations, and a future 3D agent floor should use separate modules and the existing tenant-scoped APIs.

## Optional cloud compatibility

The original two-service Neon/Render path is retained only as an **optional, potentially paid alternative** in [docs/cloud-setup.md](docs/cloud-setup.md) and `docs/optional-render-two-services.yaml`. The root `render.yaml` now contains the separate single-service Free PWA preview described below. Neither cloud path is required for the free local setup. Existing cloud deployments must explicitly set `AI_PROVIDER=cloud` and their HTTPS `OPENAI_BASE_URL`; cloud mode requires a provider key. Never deploy the Render template expecting zero charges. Creating resources, deploying services, or making paid AI calls still requires your approval.

Ollama and the application frameworks are MIT-licensed; Podman and the chosen Qwen model use Apache 2.0; PostgreSQL uses the PostgreSQL License. Third-party licenses still apply. Check the license before choosing a different model, especially for commercial client use.

## Installable PWA and Render

The dashboard now supports browser installation on desktop and mobile, with a manifest, app icons, install guidance, and a safe offline page. Business/account data remains online-only and is not cached by the service worker.

For the new **single-service Free Render preview**, see [docs/render-pwa.md](docs/render-pwa.md). The root `render.yaml` uses one Free plan and leaves hosted AI disabled to avoid paid inference. It needs an external persistent PostgreSQL database, a pushed Git repository, and deployment approval. The free local Compose setup above continues to provide the complete local Ollama experience. The older cloud instructions describe an optional alternative, not the new root Blueprint.

## Account access — contact the owner

Public account creation is disabled to prevent automated signup abuse. The sign-in page provides **Request access by email** at **tmcwilliams2010@outlook.com**; this opens the visitor's email app and does not submit a server form or automatically create an account. The legacy `POST /auth/register` endpoint always returns 403, including requests with old owner-setup codes. Browser owner-setup links no longer open a registration form. Previously created accounts continue to sign in.

To approve a business, sign in as an administrator and open **Business settings**. Create the business, then either create a manual temporary-password account or—after email delivery is configured—send a single-use setup invitation. Assign Viewer, Responder, or Manager access. Clients cannot provision accounts, grant themselves roles, publish agent configuration, or access another business. Administrators can disable accounts; the final active administrator cannot be disabled.

### Optional email recovery and invitations

Recovery, verification, and invitation screens are included, but delivery defaults to off. Keep `EMAIL_PROVIDER=disabled` unless you have an HTTPS delivery account and a verified sender. The recommended free hosted-PWA option is Brevo Free: after Brevo approves the free account and verifies the sender, set `EMAIL_PROVIDER=brevo`, store `EMAIL_API_KEY` only as a Render secret, set `EMAIL_FROM` to the exact verified sender (for example `Agent Meadow <tmcwilliams2010@outlook.com>`), and keep `APP_ORIGIN` on the public HTTPS origin. The older `resend` adapter remains supported. Restart after changing these settings. The application never uses ordinary outbound SMTP, never reads an inbox, never stores raw action tokens, and reports delivery as unavailable while configuration is incomplete. `EMAIL_PROVIDER=test` is rejected outside the test environment.

Brevo's published Free plan currently requires no credit card and permits up to 300 emails per day after account approval; plan terms can change. Agent Meadow retains a lower configurable default of 50 security emails per day. Brevo can verify a sender by emailing a six-digit code when its domain is not authenticated. Using a free Outlook sender avoids a paid domain but may reduce deliverability. Do not paste the API key into chat, source control, or Agent Meadow's browser UI—enter it directly in Render's secret environment settings.

Action links expire, are purpose-bound and single-use. Password recovery revokes all sessions for that account. The public forgot-password response does not reveal whether an email address exists. No real message is sent by the automated test suite.

For a fresh installation only, run `python -m app.bootstrap` from `backend/` in a trusted environment connected to its database; it prompts privately for the initial administrator password and refuses when an administrator already exists. The existing deployed owner account does not need to be recreated. The historical `OWNER_SETUP_TOKEN_HASH` setting is ignored by the retired registration endpoint, and migration `0003` is retained for existing database history; no database reset or migration is needed to close signup.

## Milestone 2 · Meadow Commons

The **Agent floor** opens an original meadow-inspired operations view. Agent stations, paths, pond, plants, pavilion, and inspector are authored SVG/HTML/CSS; no external floor implementation or artwork is imported. The floor reads real agent, conversation, token, activity, and handoff data scoped to the selected business. It is a lightweight interactive isometric view, not a full WebGL simulation. See `docs/design-origin.md` for provenance.

- **Knowledge:** administrators can add/edit/disable business facts or import `.txt`/`.md` content in the browser. Each business supports up to 100 documents of 20,000 characters. The model receives the four highest-scoring matching chunks from that business using bounded lexical retrieval; no paid embedding service is used. The assistant's stored response includes the reference document titles/IDs. Documents are treated as reference facts, not trusted model instructions. This is simple lexical grounding, not semantic/vector search.
- **Contact capture:** chat's explicit consent checkbox enables capture of an email voluntarily shared in the current user message. The saved lead links to its conversation and records its source. Repeat emails within the same conversation are deduplicated. No assistant-generated contact information is harvested; AI failures do not save a partial turn or lead. This uses deterministic email extraction, not model hallucinated details or email verification.
- **Human handoff:** users can request a person before or during chat. AI pauses while requested/human handling is active. Users can continue adding messages to that inbox without invoking inference. An administrator takes over, sends human replies, resolves, or resumes AI. Replies refresh on demand; no external notifications or continuous presence are implied.
- **Inference:** the status panel distinguishes configuration from actual reachability. Administrators can explicitly check the configured `/models` endpoint. `AI_PROVIDER=bridge` supports your authenticated HTTPS Ollama bridge on Linux. Follow `docs/linux-inference.md`; the hosted app remains disabled until your machine and endpoint are ready. The bridge uses only free software, but your hardware/network availability and tunnel-provider terms still apply.

Apply migration `0004` before starting the new version. It preserves existing data while adding knowledge, response sources, handoff fields, and conversation-linked lead capture. Tests cover cross-tenant retrieval, disabled documents, source persistence, consent/deduplication, human takeover/resume, floor statistics, and bridge authentication/request limits.

## Guided Ollama connection

Run `python3 scripts/setup_ollama.py` from the project root on your own Linux machine. It prepares rootless Ollama, pulls the local model, verifies a response and token usage, starts the protected bridge/temporary HTTPS tunnel, and creates a private Render configuration file. It does not change the hosted app or publish credentials automatically. See [the Linux guide](docs/linux-inference.md) for prerequisites and the final Render connection step.

## Milestone 3

[Milestone 3 plan](docs/MILESTONE_3_PLAN.md) covers account recovery, onboarding, a public website widget, lead pipeline, team handoff management, and original floor personalization. Release A implements account access/security and resumable owner-reviewed onboarding. Its migrations are `0005` and `0006`. Release B (widget and lead pipeline) and Release C (team handoff and floor personalization) remain planned.
