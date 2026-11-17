FROM node:22-bookworm-slim
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --ignore-scripts && ./node_modules/.bin/playwright install --with-deps chromium
COPY agent.mjs mcp.mjs server.mjs ./
USER node
ENV HOST=0.0.0.0 PORT=8787
EXPOSE 8787
CMD ["node", "server.mjs"]
