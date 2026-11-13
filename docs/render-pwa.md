# Installable PWA on Render (free preview)

The PWA has an app manifest, standalone display mode, normal and maskable icons, an Apple touch icon, install instructions, and a service worker. Authenticated pages, API responses, conversations, passwords, and session tokens are never written to service-worker Cache Storage. Offline navigation shows a generic public page; reading or sending conversations requires connectivity. No background replay of chat requests occurs.

## Free Render architecture

The root `render.yaml` now defines **one free Docker web service**, running Next.js publicly and FastAPI on an internal loopback port. A supervisor runs migrations, starts both processes, forwards shutdown, and stops the service if either process exits. `/health` verifies backend/database reachability. This avoids consuming two free instance-hour budgets concurrently. The local Podman Compose setup is still supported separately.

No database or AI service is created by the Blueprint. Supply an existing PostgreSQL database with TLS (for example, a Neon free-tier database within its current quotas). Do not use SQLite on Render's ephemeral disk. Render's free PostgreSQL expires after 30 days, so this template does not provision one. Select and review any external provider's limits yourself before connecting it.

Current Render docs checked during this task state that free web services sleep after 15 minutes idle, take about a minute to wake, share 750 instance hours per workspace/month, and have ephemeral storage. Render describes free instances as unsuitable for production. Bandwidth/build-minute limits also apply; if a payment method is attached, overages may incur charges. Check account spend settings and the current limits at https://render.com/docs/free before publishing. This is a free preview configuration, not a guarantee of permanent free production hosting.

**AI is disabled by default** (`AI_PROVIDER=disabled`), preventing any paid inference calls. Accounts, agent configuration, leads, history, and metrics work with the supplied database. Chat returns an explicit 503 until inference is configured. Ollama on your laptop cannot be reached from Render via localhost, and its model files cannot persist on a free Render instance. The complete free local stack still supports Ollama inference. A hosted inference provider needs a separately reviewed endpoint, credentials, quotas, and any required spending approval; the Blueprint does not configure one automatically.

## Publishing checklist

1. Push this project, including `Dockerfile`, `render.yaml`, and PWA assets, to GitHub/GitLab/Bitbucket. The project repository is https://github.com/temcwilliams/AIAGENTSAAS. Merge the PWA implementation before creating the Blueprint.
2. In Render, create a Blueprint from that repository. Verify **one web service, Free plan, no databases, no paid resources** before applying it. Automatic deploys and preview environments are off; initial Blueprint application still deploys.
3. Set `APP_ORIGIN` to the exact final frontend HTTPS URL (no trailing slash), such as `https://YOUR-SERVICE.onrender.com`. Update it if Render assigns a different name.
4. Set `DATABASE_URL` (pooled) and `DATABASE_URL_UNPOOLED` (direct) as secrets using `postgresql+psycopg://...?...sslmode=require` URLs. Use `?sslmode=require` when there is no existing query; use `&sslmode=require` when adding to one. Never commit passwords. In production, supply a dedicated database/branch and review backups first.
5. Approve the deployment and schema migration before clicking Apply. The startup command executes `alembic upgrade head` on each start, including cold starts. Do not run multiple copies or scale this preview design during migrations.
6. Bootstrap the first administrator from a trusted terminal connected to the target database: from `backend`, run `python -m app.bootstrap` with the production database and app-origin environment configured. Free services do not provide a dashboard shell; do not expose bootstrap as a public API.
7. Verify HTTPS, `/health`, sign-in, tenant isolation, and the manifest at `/manifest.webmanifest`. On Chrome/Edge use the install button/menu. On iOS use Safari → Share → Add to Home Screen. Test offline navigation and reconnection on a real device.

Render's Blueprint creation page is https://dashboard.render.com/blueprints . After merging the implementation, use https://dashboard.render.com/blueprint/new?repo=https://github.com/temcwilliams/AIAGENTSAAS.

No deployment was performed by generating these files. Render CLI is not installed in this workspace; public JSON-schema validation is available here, but platform-aware validation and actual Render startup still need verification before publication. The previous two-service paid-capable template is retained as `docs/optional-render-two-services.yaml` for reference only.

## Repeatable browser verification

After `npm run build`, start the combined supervisor locally with a disposable SQLite database (test environment only):

```sh
ENVIRONMENT=test DATABASE_URL=sqlite:////tmp/pwa-test.db APP_ORIGIN=http://localhost:3188 AI_PROVIDER=disabled PORT=3188 .venv/bin/python scripts/run_render.py
```

In another terminal, install Playwright as an optional test tool (`npm install --no-save playwright` from `frontend`, then `npx playwright install chromium`) and run `node frontend/tests/pwa-smoke.cjs` from the project root. Set `PWA_TEST_URL` for a different URL. The script verifies manifest/icons, service-worker control and cache headers, public-only cached assets, offline fallback, reconnection, install instructions, and `/health`. Actual native installation on iOS/Android still needs a device check.

If Render CLI is installed, run `render blueprints validate render.yaml` before applying the Blueprint. Schema validation alone does not verify account quotas or live startup.
