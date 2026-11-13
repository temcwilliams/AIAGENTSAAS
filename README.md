# Agent Meadow · PWA and free local edition

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

The suite tests authentication, session expiry/revocation, password changes, admin permissions, tenant isolation, composite database constraints, shared business request limits, conversation/token persistence, failed-provider rollback, and both local/cloud provider adapters. Tests use isolated SQLite databases and mocked AI responses. No paid calls occur. PostgreSQL locking and live Ollama inference require separate integration validation. CI configuration is included under `.github/workflows`.

## Architecture and security

`backend/app/security.py` handles identity and tenant authorization; `limits.py` owns atomic request limits; `ai.py` isolates inference; `models.py` owns persistence; `schemas.py` validates requests; `main.py` exposes REST endpoints. Next.js UI and same-origin API proxy live under `frontend/src/app`. OpenAPI docs are available at `/docs` on the API when accessed within the container network or through native development.

Passwords use Argon2id. Sessions use random tokens stored only as digests. The Create account form signs up clients into newly created, isolated businesses. Platform owner setup requires a private one-time setup token; the first public visitor never becomes an administrator. Offline admin bootstrap remains available. All business endpoints enforce tenant authorization and scope resource queries. Admins intentionally manage all businesses. Composite foreign keys reject mixed-tenant references. Writes require the configured Origin. Password changes revoke every session; “sign out everywhere” is available to clients and admins. PostgreSQL locks serialize chat turns. The initial schema and rate-limit migration are included and run before the container API starts.

Leads are manually recorded by admins; performance metrics are request, conversation, lead, and token counts. Email-based recovery, MFA, audit trails, automated retention, and per-tenant token budgets remain future work. Billing, integrations, and a future 3D agent floor should use separate modules and the existing tenant-scoped APIs.

## Optional cloud compatibility

The original two-service Neon/Render path is retained only as an **optional, potentially paid alternative** in [docs/cloud-setup.md](docs/cloud-setup.md) and `docs/optional-render-two-services.yaml`. The root `render.yaml` now contains the separate single-service Free PWA preview described below. Neither cloud path is required for the free local setup. Existing cloud deployments must explicitly set `AI_PROVIDER=cloud` and their HTTPS `OPENAI_BASE_URL`; cloud mode requires a provider key. Never deploy the Render template expecting zero charges. Creating resources, deploying services, or making paid AI calls still requires your approval.

Ollama and the application frameworks are MIT-licensed; Podman and the chosen Qwen model use Apache 2.0; PostgreSQL uses the PostgreSQL License. Third-party licenses still apply. Check the license before choosing a different model, especially for commercial client use.

## Installable PWA and Render

The dashboard now supports browser installation on desktop and mobile, with a manifest, app icons, install guidance, and a safe offline page. Business/account data remains online-only and is not cached by the service worker.

For the new **single-service Free Render preview**, see [docs/render-pwa.md](docs/render-pwa.md). The root `render.yaml` uses one Free plan and leaves hosted AI disabled to avoid paid inference. It needs an external persistent PostgreSQL database, a pushed Git repository, and deployment approval. The free local Compose setup above continues to provide the complete local Ollama experience. The older cloud instructions describe an optional alternative, not the new root Blueprint.

## Create account

Use **Create account** on the sign-in screen to enter a business name, email, and password (12–128 characters), then confirm the password. Successful signup creates an isolated business and client account and signs the user in. Signup cannot select a role or join an existing business. Duplicate emails are rejected without creating extra businesses. Email ownership verification is not yet implemented.

For the initial platform administrator, the operator sets `OWNER_SETUP_TOKEN_HASH` to the SHA-256 digest of a cryptographically random token and privately delivers a link using `#owner-setup=TOKEN`. The browser removes the fragment from history and submits the token only in the HTTPS registration body. The raw token must never be committed, logged, or included in a public URL query. Alternatively, paste it into **Have an owner setup code?**. A unique database claim makes owner setup one-time and prevents concurrent requests from creating multiple platform owners. An existing administrator also closes owner setup. Ordinary signups always remain clients.

Revision `0003` adds the owner-setup claim table. Signup is limited to 50 attempts per hour globally and five per email, shared across workers. Treat the private owner setup link as a credential. It is consumed only when account creation succeeds.

## Milestone 2 · Meadow Commons

The **Agent floor** opens an original meadow-inspired operations view. Agent stations, paths, pond, plants, pavilion, and inspector are authored SVG/HTML/CSS; no external floor implementation or artwork is imported. The floor reads real agent, conversation, token, activity, and handoff data scoped to the selected business. It is a lightweight interactive isometric view, not a full WebGL simulation. See `docs/design-origin.md` for provenance.

- **Knowledge:** administrators can add/edit/disable business facts or import `.txt`/`.md` content in the browser. Each business supports up to 100 documents of 20,000 characters. The model receives the four highest-scoring matching chunks from that business using bounded lexical retrieval; no paid embedding service is used. The assistant's stored response includes the reference document titles/IDs. Documents are treated as reference facts, not trusted model instructions. This is simple lexical grounding, not semantic/vector search.
- **Contact capture:** chat's explicit consent checkbox enables capture of an email voluntarily shared in the current user message. The saved lead links to its conversation and records its source. Repeat emails within the same conversation are deduplicated. No assistant-generated contact information is harvested; AI failures do not save a partial turn or lead. This uses deterministic email extraction, not model hallucinated details or email verification.
- **Human handoff:** users can request a person before or during chat. AI pauses while requested/human handling is active. Users can continue adding messages to that inbox without invoking inference. An administrator takes over, sends human replies, resolves, or resumes AI. Replies refresh on demand; no external notifications or continuous presence are implied.
- **Inference:** the status panel distinguishes configuration from actual reachability. Administrators can explicitly check the configured `/models` endpoint. `AI_PROVIDER=bridge` supports your authenticated HTTPS Ollama bridge on Linux. Follow `docs/linux-inference.md`; the hosted app remains disabled until your machine and endpoint are ready. The bridge uses only free software, but your hardware/network availability and tunnel-provider terms still apply.

Apply migration `0004` before starting the new version. It preserves existing data while adding knowledge, response sources, handoff fields, and conversation-linked lead capture. Tests cover cross-tenant retrieval, disabled documents, source persistence, consent/deduplication, human takeover/resume, floor statistics, and bridge authentication/request limits.
