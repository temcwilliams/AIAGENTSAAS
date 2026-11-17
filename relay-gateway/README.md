# Relay plugin gateway

A separate, authenticated Node 22+ service for the Relay PWA. Runs the official Microsoft Playwright MCP server and an Ollama tool loop. Does not change Agent Meadow, require an App Store app, or turn the static PWA into a code-execution host. No paid model API is used.

## Supported integration

- **Ponytail 5.3.3:** official skill text is bundled in the PWA from upstream commit `96608e078b2d5ea607c5c3b8b5a54d1c1fba6846`, with its MIT license. Lite/full/ultra/off and review/audit/debt/help/gain skill dispatch apply real upstream instructions to model requests. This is the upstream portable instruction/skill integration, not a Claude Code runtime. Claude-specific hooks, band/board metrics and subagent injection are unavailable. Whole-repo commands need repository content provided in chat; Relay has no filesystem/coding-execution connector and must not claim to have audited unseen files.
- **Playwright MCP 0.0.85:** the gateway negotiates MCP, discovers current tool schemas, passes them to Ollama, runs approved calls, returns real results and browser snapshots/screenshots, and continues the model/tool loop. Each conversation gets an isolated temporary browser profile and a temporary output directory. No personal browser session/cookies are imported. Playwright runs on the gateway server, not the user's phone.
- Every browser tool step is proposed first and requires explicit PWA approval. The server stores exact pending calls; clients cannot replace arguments on approval or replay it. Decline/Escape/Stop prevent pending actions. Up to 4 calls per approved batch and 8 tool rounds per user turn; 2 concurrent sessions by default, 15-minute idle expiry.
- Direct Node/server code-execution tools (`browser_run_code`/`browser_run_code_unsafe`) are intentionally not exposed. Normal browser automation and page evaluation remain available with approval. WebMCP tools are disabled; plugin subprocess credentials are scrubbed and its cwd is a temporary directory. These are defense measures, not an OS sandbox guarantee: deploy a dedicated browser service/container with no sensitive host files. Full arbitrary GitHub repository execution/installation is not supported.

## Run beside your Ollama server

1. Install Node 22+ on the server. Copy/clone this repository and enter `relay-gateway`.
2. `npm ci --ignore-scripts`
3. `npx --no-install playwright install --with-deps chromium` (Linux dependencies may require administrator access). Alternatively set `RELAY_BROWSER_EXECUTABLE` to an installed compatible Chromium.
4. Copy `.env.example` to `.env`. Generate a token using the command shown there; put it in `RELAY_GATEWAY_TOKEN`. Do not commit or paste the token into chat. Configure `OLLAMA_URL` to the server's Ollama base URL and `OLLAMA_TOKEN` only if its proxy needs one. These secrets stay server-side.
5. `node --env-file=.env server.mjs`
6. Put an authenticated-by-token HTTPS reverse proxy in front of `127.0.0.1:8787` and keep the private listener/firewall boundary intact. For example a Caddy site at your own hostname can reverse_proxy to `127.0.0.1:8787`. Configure DNS/TLS through your chosen host. Do not proxy this through the existing Agent Meadow service.
7. In Relay, open **Plugins**, enter your HTTPS gateway URL and gateway token, connect, then enable Playwright. Choose an installed Ollama model that supports tool calls. Models that do not support tools return an explicit error; a model being named “coder” does not establish tool support. Start a typed chat and approve/decline each proposed action.

The gateway URL is remembered locally in the PWA. Its access token is kept in session memory only and cleared on Disconnect. Changing/turning off the browser plugin restores the PWA's direct Ollama connection. Voice is disabled for browser-tool mode so actions require typed requests and visible approval.

Your server was not yet configured when this integration was authored. This repository does not supply an Ollama endpoint, model download, DNS, TLS certificate, or production gateway token. Publishing the PWA controls alone does not make Playwright available: steps above must be completed on your host.

## Container option

Build with `docker build -t relay-plugin-gateway .`. Supply environment variables securely and publish only `127.0.0.1:8787:8787` behind your HTTPS proxy; use `--init` for process cleanup. Set `OLLAMA_URL` to an address reachable from the container (a private Docker network is preferred; host loopback is a different network namespace). Do not mount home directories or host credentials. The image installs the pinned package's matching Chromium rather than assuming another image's browser version.

Chromium sandbox support depends on your host/container configuration. Keep it enabled where available and use a suitable non-root/seccomp setup. `RELAY_MCP_NO_SANDBOX=1` is a diagnostic override for an already isolated development/container environment; it was needed in the temporary test sandbox and is not the default. A browser needs adequate server memory/disk; this is not promised to fit every free hosting tier. The Docker image was not built in the authoring environment.

## API and boundaries

All `/v1/*` routes require the bearer token. Allowed origins are exact entries from `RELAY_ALLOWED_ORIGINS` (comma-separated); no wildcard/credentialed-cookie CORS. Public `/health` returns only liveness. Request bodies are bounded to 256 KB; responses 4 MB; Ollama requests have deadlines and reject redirects. Inference credentials are not accepted from client requests. Sessions/context are in memory and are lost on restart. Single-owner bearer access is not multi-tenant authentication.

- `GET /v1/status`: installed models and supported plugin identity.
- `POST /v1/chat`: model/messages and optional active session. Returns a completed reply or pending approval.
- `POST /v1/continue`: session, exact approval ID, boolean allow. Executes server-stored calls only.
- `DELETE /v1/session`: close the browser and cancel in-flight inference.

Tool text and screenshots are untrusted; the PWA renders text with textContent and permits only PNG/JPEG/WebP image data. Page instructions are not authorization. Review all arguments, especially forms, uploads, navigation, and page scripts. No persistent browser profiles, account-sign-in automation, external messages, or production mutations were used during verification.

## Verification

`npm test` covers approval gating, argument binding/replay rejection, decline, forged tool history, authentication, CORS and body limits using a mocked model/plugin.

`RELAY_BROWSER_EXECUTABLE=/path/to/chromium node test/playwright.integration.mjs` exercises the real official MCP server against a disposable loopback fixture: tool discovery, navigation, accessibility data, click, screenshot, unsafe host-code exclusion and session cleanup. Use the sandbox override only when necessary in your isolated test environment.

The PWA `relay/tests/plugins.browser.cjs` tests gateway setup/models, pinned Ponytail instructions in outgoing requests, approve/decline/Escape/Stop, inert tool text, token non-persistence and restoration with a mocked gateway. This is not real Ollama inference evidence. Production gateway hosting, model tool quality and physical-phone operation remain unverified until your host is connected.
