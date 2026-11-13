FROM node:22-bookworm-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

FROM python:3.12-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends libstdc++6 && rm -rf /var/lib/apt/lists/*
COPY --from=web /usr/local/bin/node /usr/local/bin/node
WORKDIR /app
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir --upgrade pip==26.3 && pip install --no-cache-dir -r backend/requirements.txt && useradd --create-home app
COPY --chown=app:app backend/app ./backend/app
COPY --chown=app:app backend/migrations ./backend/migrations
COPY --chown=app:app backend/alembic.ini ./backend/alembic.ini
COPY --chown=app:app scripts/run_render.py ./scripts/run_render.py
COPY --from=web --chown=app:app /web/.next ./frontend/.next
COPY --from=web --chown=app:app /web/public ./frontend/public
COPY --from=web --chown=app:app /web/node_modules ./frontend/node_modules
COPY --from=web --chown=app:app /web/package.json ./frontend/package.json
COPY --from=web --chown=app:app /web/next.config.ts ./frontend/next.config.ts
ENV NEXT_TELEMETRY_DISABLED=1 NODE_ENV=production
USER app
EXPOSE 10000
CMD ["python", "scripts/run_render.py"]
