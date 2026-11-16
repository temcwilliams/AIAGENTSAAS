# Agent Meadow — project progress

Last updated: **2026-11-16, 17:19 UTC**  
Maintained as an ongoing project log. Read this file when starting or resuming work, and update it as meaningful work completes.

## Current status

**Account access is owner-approved only, deployed and verified.** Public Create account and browser owner setup are removed. Businesses use **Request access by email** at `tmcwilliams2010@outlook.com`; the owner provisions approved businesses/clients through **Business settings**. The retired signup endpoint returns 403 before database/password work. Existing sign-in remains available. Independent red-team tests found no signup/provisioning bypass; the complete backend suite now has 68 passing tests. Strix is no longer on the active checklist.

**Security release is live and verified.** [PR #5](https://github.com/temcwilliams/AIAGENTSAAS/pull/5) fixes request-size, authentication resource, conversation locking/storage abuse issues and patches dependency advisories. Independent local red-team regressions and GitHub checks passed. Public health, access protections, request limits, and PWA smoke checks passed after deployment on 2026-11-15. Strix remained blocked by authentication prompts; no Strix scan ran or credits were spent. The 2026-11-13 npm/pip audits reported zero known vulnerabilities after updates; this is not a comprehensive external penetration test.

**Agent Meadow is deployed and healthy.** Milestone 1 and the Milestone 2 application features are live. Live AI inference is **not enabled**: the user's Linux Ollama bridge still needs to be connected.

| Item | Status / location |
|---|---|
| Application | [Open Agent Meadow](https://agent-studio-pwa-girg.onrender.com) |
| Source repository | [temcwilliams/AIAGENTSAAS](https://github.com/temcwilliams/AIAGENTSAAS) |
| Render workspace | `Ai agent SaaS` |
| Render service | `agent-studio-pwa-girg`, **Free** plan |
| Render dashboard | [Service dashboard](https://dashboard.render.com/web/srv-dbriv0l6e07s73bs7p7g) |
| Database | Neon project `aiagentsaas`, **Free** organization plan |
| Live database migration | `0004` |
| Latest verified live application commit | `4f139c64808643fff725c86021dc520294c9d976` |
| Latest verified live deployment | `dep-dbtjk7ei0phs73di7410` |
| Automatic deployments | Disabled; application releases are deployed manually |
| Hosted AI | `AI_PROVIDER=disabled` |
| Latest complete backend suite | **68 tests passed** (includes 19 local red-team regressions) |
| Milestone 3 | [Six-workstream plan](docs/MILESTONE_3_PLAN.md) prepared for review; implementation not started |
| Guided Linux setup | [Setup script](scripts/setup_ollama.py) ready; user still needs to run it on their Linux machine |
| Initial administrator | Created through one-time owner setup; initial sign-in was verified |
| Pilot business / starter agent | **Not created**; saved setup credentials were rejected during later verification |

The public hostname retains the original service name; the application, browser metadata, and installed PWA are branded **Agent Meadow**. The application commit above intentionally differs from later documentation-only commits.

## Requirements and decisions

- Build a hybrid service: the platform owner manages agents for client businesses; clients have isolated dashboards for their own business.
- Use Next.js, TypeScript, Tailwind CSS, FastAPI, and PostgreSQL. Keep billing, integrations, and later visualization work modular.
- Prefer free, open-source software and free service plans. No paid model calls or paid resource plans have been used for the recorded work. Free hosting still has quotas, sleep behavior, and availability limits.
- The intended repository is `temcwilliams/AIAGENTSAAS`. The user clarified that their originality concern was about an external **agent-floor reference**, not about replacing this repository.
- The **Meadow Commons** floor was authored for Agent Meadow. No external agent-floor implementation, artwork, sprites, or 3D assets were imported. See [design provenance](docs/design-origin.md).
- The user chose a **Linux computer/server** for free Ollama inference. Its address and authenticated connection are not yet configured.
- The user approved the Render deployment, use of the new workspace, storage of the Neon database credentials in that service, and configuration of the one-time owner setup verifier. Those setup approvals were obtained explicitly after automatic review required them.
- Keep passwords, API keys, bridge tokens, database connection strings, and private account-setup links out of this document and source control.

## Completed work

### Milestone 1 — platform foundation

- [x] Actual frontend and backend project files, dependency manifests, environment templates, setup documentation, and CI workflow.
- [x] Argon2id password hashing; opaque server-side sessions stored as digests; cookie security settings; expiry and logout revocation.
- [x] Administrator and client roles, enforced tenant authorization, business-scoped resource queries, and composite foreign keys against mixed-tenant references.
- [x] Business creation/management and client account creation.
- [x] Agent creation/configuration: model, instructions, temperature, output limit, and enabled state.
- [x] OpenAI-compatible chat adapter with real provider responses and usage accounting; no fake production fallback.
- [x] Conversation/message storage, token totals, lead dashboard, and business performance summaries.
- [x] Alembic migrations and REST API routes.
- [x] Authentication, role, tenant isolation, route, persistence, and provider-failure tests.

### Security and account usability

- [x] Atomic login throttling shared across backend workers.
- [x] Password-change UI that revokes all of the user's sessions.
- [x] Sign-out-everywhere action.
- [x] Configurable business-wide chat attempt limits, including failed provider attempts.
- [x] Workspace state resets and protection against late refresh results from a previously selected business.
- [x] Public **Create account** form was implemented earlier; now retired in code at the user’s request (deployed 2026-11-16). Sign-in offers an email request link instead.
- [x] Only administrators can provision business/client accounts; public registration returns 403 in code, including legacy owner tokens (deployed 2026-11-16).
- [x] Historical one-time owner signup created the initial administrator; browser owner registration is now retired and deployed. Existing owner claims are retained; fresh installations use offline bootstrap.
- [x] Retired owner-link fragments are scrubbed without exposing a registration form.
- [x] Initial administrator created at the user's request, with generated credentials delivered privately; the verification session was signed out.

**Current access limitation:** the originally generated administrator password was rejected during Milestone 2 live verification. The cause was not assumed, the password was not reset, and authentication was not bypassed. The user should sign in with their current password. A later account-recovery feature is still outstanding.

### Free local edition

- [x] Local PostgreSQL + Ollama stack using Podman-compatible Compose.
- [x] Random local database password generator that refuses to overwrite an existing secret file.
- [x] Backend/frontend container files, loopback-only published frontend, and persistent database/model volumes.
- [x] Default local model configuration for `qwen2.5:1.5b`.
- [x] Local inference works without a paid API key; cloud credentials are never forwarded to local Ollama.
- [x] Local endpoint restrictions, bridge/cloud modes, and an explicit disabled mode.
- [x] Free-software setup instructions and clear distinction between free software and hosting/hardware costs.
- [x] Guided rootless Linux setup script with private reusable token storage, verified official publisher downloads, local inference/usage validation, protected bridge, temporary HTTPS tunnel, and a private Render configuration file. The script is prepared and tested; the user must run it on their Linux host.

### Installable PWA and Render deployment

- [x] Manifest, standalone display mode, normal/maskable icons, Apple touch icon, install guidance, and offline fallback.
- [x] Service worker caches only public offline assets. Authenticated pages and API responses are not persisted in its Cache Storage.
- [x] One Free Docker web service runs Next.js and loopback-only FastAPI under a process supervisor.
- [x] Startup migrations, process shutdown handling, and a public `/health` endpoint checking backend/database readiness.
- [x] Existing GitHub repository initialized and application source published; initial draft PR reviewed through checks and merged.
- [x] User-created Render workspace detected and used; the earlier `My Workspace` was not used for this deployment.
- [x] Separate free Neon project created, with pooled runtime and direct migration connections and TLS.
- [x] Real Docker build completed on Render, deployment reached `live`, and public health/assets/access checks passed.
- [x] Application renamed from Agent Studio to **Agent Meadow**, including PWA metadata and offline cache migration.

### Milestone 2 — original floor and operational workflows

- [x] **Meadow Commons** original floor: garden terrain, winding paths, plant-like agent stations, reflection pond, handoff pavilion, and station inspector.
- [x] Keyboard-accessible station controls, list alternative, pagination beyond six stations, responsive layout, and explicit empty-workspace state.
- [x] Floor reads real tenant-scoped agents, conversations, AI reply counts, token totals, last message activity, and open handoffs. It does not invent worker activity.
- [x] Business knowledge editor and browser import of plain text/Markdown files; administrator-managed enable/disable controls.
- [x] Bounded lexical retrieval from the selected business's documents, reference-context boundaries, and stored document references on responses.
- [x] Explicit opt-in contact capture from email details voluntarily shared in the current user message; conversation linkage and duplicate protection.
- [x] Human handoff requests pause AI. Users can continue sending inbox messages without invoking a model.
- [x] Administrator takeover, human replies, resolution, and AI resumption; replies and floor snapshots refresh on demand.
- [x] Inference status panel distinguishes configuration from reachability; explicit administrator connection check.
- [x] Authenticated Linux Ollama bridge with fixed loopback upstream, request/body/context/output/concurrency limits, and safe malformed-header rejection.
- [x] Migration `0004` tested and deployed with existing data preserved.
- [x] [Linux connection instructions](docs/linux-inference.md) and [original design record](docs/design-origin.md).

**Floor scope:** this is an interactive isometric SVG/HTML/CSS design, not a full WebGL 3D simulation. The API is separate from its presentation so a future 3D implementation can reuse it.

## Verification and evidence

| Area | Result | Scope / limit |
|---|---|---|
| Backend tests | **68 passed** | One upstream TestClient/httpx deprecation warning; no failing tests |
| Frontend production build | Passed | Includes TypeScript validation |
| GitHub checks | Passed for owner-approved access release | PR #6 merged; frontend/API jobs and both push/PR runs succeeded. PR #7 red-team test/report follow-up merged after both push/PR workflows passed |
| SQLite migration round trips | Passed | Includes populated-data preservation and full downgrade/reapply in disposable databases |
| PostgreSQL migration | Passed on isolated Neon branch | Generated migration SQL applied; original row counts unchanged |
| Production schema | Verified at `0004` | Application startup migrations completed on Render |
| Browser workflows | Passed locally | Knowledge → cited response → consented lead → handoff → takeover → human reply; disposable data and a test-only model server |
| Floor responsiveness | Passed in Chromium | Desktop and mobile, with no horizontal overflow |
| Live service | Healthy after security deployment | Public `/health` returned 200; Render deploy reached live |
| Live frontend | Verified served | Bundle contains Meadow Commons, knowledge, and handoff interfaces |
| Live endpoint protection | Verified after security release | Five protected APIs returned 401; untrusted-Origin write returned 403; one 65KB request returned 413 before authentication |
| Live administrator pilot setup | Not completed | Saved setup password was rejected; no pilot business/agent was inserted |
| Ollama setup automation | 7 installer tests passed as part of the 49-test suite | Publisher files/checksum availability verified online; binary/model downloads mocked in tests |
| Real Ollama model inference | **Not verified/enabled on production** | Linux machine setup, gateway endpoint, and secret are still needed |
| Native mobile installation | Not verified on physical devices | Chromium PWA/offline behavior was verified |

Design previews retained in the working environment and shared in the conversation:

- Desktop: `artifacts/meadow-commons-desktop.png` (clearly labelled sample data).
- Mobile: `artifacts/meadow-commons-mobile.png` (clearly labelled sample data).

These local screenshots are not tracked in GitHub. They use disposable **Preview fixture** data; they are not evidence of production customer agents or live model activity. The [floor implementation](frontend/src/components/agent-floor.tsx) is tracked in the repository.

The isolated Neon branch `milestone2-validation` is retained for development validation and is not the application's runtime database branch.

## Remaining work and blockers

### Next actions

1. **Use the current administrator password.** Sign in and choose **Agent floor → Add an agent**, or create a clearly labelled pilot business first. The original private setup password should not be assumed valid.
2. **Set up the user's Linux machine.** The user confirmed that it is not set up yet. From the cloned project root, run `python3 scripts/setup_ollama.py` following [the Linux guide](docs/linux-inference.md). It prepares rootless Ollama, verifies a local response, starts the protected bridge/temporary tunnel, and creates a private Render settings file. This command has not been run on the user's machine.
3. **Connect the Linux bridge to Render.** Supply a reachable HTTPS base URL and store the matching bridge token directly in Render secrets. Then set `AI_PROVIDER=bridge` and deploy the configuration. Do not send or commit the token.
4. **Verify actual inference.** Check connectivity in the Inference screen, run one approved conversation, inspect grounding/references and token totals, and confirm performance on the actual Linux hardware.
5. **Run a small business pilot.** Add real, approved business facts, exercise consented lead capture and human handoff, and collect usability feedback.

### Planned next development milestone

The user requested that account recovery, business onboarding, website widget, lead pipeline, team handoff management, and floor personalization be planned **before implementation**. The detailed sequence and acceptance criteria are in [Milestone 3 plan](docs/MILESTONE_3_PLAN.md). Only planning/documentation has been completed; none of these new workstreams is marked implemented or deployed. The plan retains original floor design, business isolation, and free-hosting constraints.

### Before broad client access

- [ ] Email ownership verification and email-based password recovery.
- [ ] Backup/restore operations and monitoring procedures tested in the intended environment.
- [ ] Privacy/consent wording, retention/deletion policy, and audit logging decisions.
- [ ] Review abuse protection and per-tenant token/resource budgets for actual traffic.
- [ ] Physical iOS/Android install testing and accessibility review with real users.

### Future modules

- [ ] Billing and payment integration.
- [ ] Business integrations and durable background jobs.
- [ ] Automated handoff notifications and richer team assignment.
- [ ] Semantic/vector retrieval if bounded lexical retrieval becomes insufficient.
- [ ] Richer agent performance/quality evaluation.
- [ ] Full 3D visualization and live presence/event updates, if desired.

## Release and decision history

The table below records work from **2026-11-13**. Later dated updates follow this table. Exact individual clock times were not recorded for every early step.

| Stage | Work / outcome | Evidence |
|---|---|---|
| Foundation | Next.js/FastAPI/PostgreSQL application created | Initial suite: 15 passed |
| Account hardening | Password changes, session revocation, shared request limits | Expanded suite: 21 passed |
| Free local setup | Podman/PostgreSQL/Ollama configuration and local-key protections | Expanded suite: 27 passed |
| PWA preparation | Installation assets, offline page, Render configuration | Expanded suite: 28 passed |
| Initial GitHub release | Repository initialized; application PR merged | [PR #1](https://github.com/temcwilliams/AIAGENTSAAS/pull/1), `eb0021940b60e36acb441d8ee29a83af0b96fe33` |
| First deployment | New Render workspace and separate Neon project; Free service live | `dep-dbriv0t6e07s73bs7q00`, schema `0002` |
| Browser account creation | Signup and private owner setup; same-tab link fix | [PR #2](https://github.com/temcwilliams/AIAGENTSAAS/pull/2), 35 tests passed, schema `0003` |
| Branding | Renamed application/PWA to Agent Meadow | `6b8b463d746e8d021a178c1d222dfe88cdd5c566` |
| Owner account | One-time signup used; administrator access/sign-in verified | Credentials delivered privately, not committed |
| Floor originality | User confirmed existing repository; external floor reference excluded | [Design record](docs/design-origin.md) |
| Milestone 2 | Original floor, knowledge/citations, contact capture, handoff, Linux bridge | [PR #3](https://github.com/temcwilliams/AIAGENTSAAS/pull/3), 42 tests passed |
| Milestone 2 deployment | Release live, PostgreSQL schema updated | `16bc5403a06c8ae716c7fcff3b0adda07259f671`, `dep-dbrjnelckfvc73efg3tg`, schema `0004` |
| Ongoing tracking | This canonical progress document and repository update instructions added | Documentation-only update; no application deployment needed |
| Milestone 3 planning | User requested all six proposed workstreams, with planning first. Detailed plan prepared for review | Documentation only; no code, migrations, emails, credentials, or deployment changes |
| Ollama connection preparation | User confirmed Linux host is not set up. Added guided setup and tests; official Linux publisher asset names/checksums checked | 49 tests passed; hosted AI remains disabled pending execution on the user's machine and Render configuration |

## How this file will be maintained

- Update the current status, relevant checklist, verification results, blockers, and history after meaningful implementation, test, migration, deployment, or user-decision changes.
- State what is implemented, what is actually deployed, and what has been verified separately.
- Identify test fixtures and mocked providers; never report them as production data or real model calls.
- Record actual outcomes, commit/deployment identifiers, and known limits; do not invent successful checks or dates.
- Keep resolved history, but ensure the top status and remaining-action list reflect the latest evidence.
- Never include secrets or private account files. Source code, screenshots, and credentials have different handling requirements.
- A documentation-only update does not imply or require a new production deployment.

### Latest Ollama setup check

The read-only setup doctor reported that this temporary development workspace has no Ollama or Cloudflare connector installed and only approximately 0.67 GiB free storage. The installer requires at least 6 GiB free to avoid starting a download it cannot complete. This workspace has not been used as a production inference host. No model was downloaded, no live Ollama inference was claimed, and no paid cloud model was selected.

The actual remaining handoff is to run the setup on the user's Linux computer/server, keep it online, and copy the resulting three private environment settings into Render. The script does not transmit credentials or deploy Render automatically. No application redeployment is needed merely to publish the installer.

### 2026-11-13 — security review and local verification

An independent local red-team review found availability/storage issues and dependency advisories. Implemented bounds before JSON parsing (64,000 bytes on both API layers), one concurrent Argon2 operation per backend worker, a shared 30/minute login budget, nonwaiting PostgreSQL conversation locks with retryable 409 responses, off-event-loop synchronous database work, and a 120/hour per-business conversation creation budget. Existing per-email and tenant controls remain enforced. Upgraded Next.js to 15.5.29 with patched PostCSS/sharp overrides; FastAPI/Starlette, pytest, and build-tool pip versions were patched. No schema migration or credential changes are required.

Latest completed full suite: **65 passed**, including 16 adversarial regressions, with one upstream TestClient deprecation warning. Frontend body helper: **3 passed**. npm audit and pip-audit report **zero known vulnerabilities** in the checked lockfile/installed environment. SQLite migration upgrade/downgrade/reapply passed. Creation-budget tests, final frontend production build, TypeScript validation, and pip dependency compatibility checks passed. PostgreSQL lock-contention tests compile the real query and simulate driver errors; they are not live PostgreSQL attack evidence. No real inference or production account mutations were used.

Strix remained blocked by repeated authentication prompts after reconnection; no Strix pentest was launched and no credits were spent. This local review is not a comprehensive external penetration test. Free-hosting capacity, account recovery/email verification, long-term retention, and monitoring remain outstanding as already recorded.

### 2026-11-15 — security release resumed

GitHub confirmed [PR #5](https://github.com/temcwilliams/AIAGENTSAAS/pull/5) is merged at `832faa0c9b5936a70436ba7b706f14e43f1d50d1`. Both branch push and pull-request workflow runs completed successfully. The existing Free Render service still served the previous release. Started manual deployment `dep-dbt120dckfvc73cfh0d0` of the merged security commit in the previously approved **Ai agent SaaS** workspace. Deployment is building; public smoke checks are pending. No new services, paid plans, model calls, or credential changes were requested.

### 2026-11-15 — security deployment verified

Deployment `dep-dbt120dckfvc73cfh0d0` reached **live** at 20:09:22 UTC, serving merged commit `832faa0c9b5936a70436ba7b706f14e43f1d50d1` on the existing **Free** service. Build and startup succeeded. No new schema revision, credentials, paid plan, or real model call was required. Recent Render error-level logs were empty during verification.

Live Chromium smoke checks passed: sign-in/Create account screen navigation; HTTP 200 health; HTTP 401 on auth/me, businesses, floor, knowledge, and handoffs without a session; HTTP 413 on one 65KB request; Agent Meadow standalone manifest/icons; no-store service-worker headers; public-only offline/icon caches; offline fallback and recovery; no browser exceptions. A separate HTTP request with an untrusted Origin returned 403. No live account was created, no customer password was used, and no authenticated data was changed. An initial separate HTTP-client path was refused/timed out; verification succeeded through Chromium and subsequent HTTP checks.

[Security review](docs/SECURITY_REVIEW.md) records the fixed findings and assessment limits. The earlier 65-test backend suite (including 16 local red-team regressions), 3 frontend request-body tests, build/type checks and migration round trip passed; GitHub frontend/API checks also passed. No new Strix scan or credit spending occurred. Ollama inference remains disabled pending the user Linux setup. This progress-only follow-up does not require another deployment.

### 2026-11-16 — owner-provisioned accounts requested

The user requested removing Create account so businesses email the owner for access, reducing automated signup/storage abuse. They explicitly supplied `tmcwilliams2010@outlook.com` for the public **Request access by email** link. Removed public signup UI and retired `POST /auth/register` with an unconditional 403 before database dependencies, schema validation, password hashing, session issuance, or owner-token processing. Existing sign-in and administrator business/client provisioning remain available. Replaced signup regression tests and the old account-creating browser smoke script with closed-signup checks; updated setup documentation and the future onboarding plan to preserve owner approval. Verification and deployment pending; no existing accounts were removed and no migration is needed.

The user also requested leaving Strix alone; it is removed from the active checklist and will not be retried unless requested. Earlier authentication failures remain historical evidence, not an action item.

Local verification passed for owner-provisioned access: **65 backend tests** (7 replacement signup/provisioning cases), **3 frontend body-limit tests**, production build and TypeScript checks, and Chromium closed-signup smoke checks (no Create account controls, correct email link, retired setup links scrubbed on load/hash change, mobile width, no browser exceptions). No real email was sent and no production account was created.

### 2026-11-16 — access release and additional red-team review

[PR #6](https://github.com/temcwilliams/AIAGENTSAAS/pull/6) merged as `4f139c64808643fff725c86021dc520294c9d976` after both GitHub push/PR workflows passed. Started deployment `dep-dbtjk7ei0phs73di7410` on the existing Free Render service; live verification is pending. The user additionally requested an independent red-team attack/review of the access change. A local reviewer is examining direct/legacy signup, account provisioning, authentication and tenant bypass using disposable fixtures; no Strix, paid scans, real emails, or production account mutations are authorized for that review. Findings and test outcomes are pending.

### 2026-11-16 — owner-approved access live; red-team verification

Deployment `dep-dbtjk7ei0phs73di7410` reached **live** at 17:16:31 UTC for merged commit `4f139c64808643fff725c86021dc520294c9d976`, on the existing Free service. Live Chromium checks passed: no Create account controls or signup fields, correct email link/address, retired owner fragments scrubbed on initial navigation and hash changes, mobile layout without horizontal overflow, and no browser exceptions. Public health returned 200; retired signup returned 403; five protected APIs returned 401; oversized input returned 413. Manifest/icons, public-only service-worker caches, offline fallback and recovery passed. Recent error-level Render logs were empty. No real email was sent and no production account was created or modified.

An independent local red-team reviewer added **3 new attack regression tests**, covering nine path/transport combinations (canonical, trailing slash, encoded path; text, form, multipart), HTTP method overrides, matching legacy owner code with an admin session, spoofed role/tenant/authentication headers, provisioning field overposting, attempted session injection and cross-tenant access. **No bypass was found**. Database/hash tripwires confirmed registration performs neither action. The new tests use disposable SQLite accounts; they are not a live authenticated penetration test. Full suite: **68 passed**, including all previous security regressions and the new cases; one upstream TestClient/httpx deprecation warning. The runtime code needs no further fix or redeployment from this review; the test/report follow-up is published in PR #7, with both GitHub push/PR workflow runs successful.

### 2026-11-16 — red-team follow-up published

[PR #7](https://github.com/temcwilliams/AIAGENTSAAS/pull/7) merged the independent attack regressions and review report after both GitHub push/PR workflows passed. There were no additional confirmed runtime vulnerabilities from this review. Production remains the verified PR #6 application commit; this follow-up only changes tests/documentation and requires no extra Render deployment. Current results: **68 backend tests passed**, **3 frontend body-limit tests passed**, build/TypeScript checks passed, closed-signup and PWA live smoke checks passed. Strix remains excluded as requested.
