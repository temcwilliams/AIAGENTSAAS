# Relay
Installable, buildless Ollama chat client. Serve `dist` over HTTPS; localhost also supports PWA development. No dependencies or build step.

## Connect
Install Ollama, then run `ollama pull llama3.2`. Use a private VPN or authenticated HTTPS reverse proxy to reach the server remotely. Do not expose unauthenticated Ollama to the public internet. Set OLLAMA_ORIGINS to the exact deployed app origin and restart Ollama. For a reverse proxy, allow GET/POST/OPTIONS, Content-Type and Authorization headers, and streaming responses without buffering. Configure OLLAMA_HOST only for the interface your proxy or VPN requires, with firewall rules limiting access.

Enter the base server URL in Server connection and click Connect. The client calls GET /api/tags and POST /api/chat using Ollama's NDJSON streaming format. Optional proxy bearer tokens remain in memory and must be reentered after reload. The URL and chats are stored locally; chat histories do not sync across devices. Demo mode provides a labeled static response, not an AI model.

## Install
Android/desktop Chrome: use Install app when available or the browser's install menu. iPhone/iPad Safari: Share → Add to Home Screen. The app shell and saved chats work offline; AI replies require access to Ollama. AI replies require a network connection to your Ollama server.

## Checks
`node --check dist/app.js` and `node --check dist/sw.js`. Browser QA and a live server connection still need verification in the target environment.

## Render deployment
Use a Render Static Site backed by GitHub, GitLab, or Bitbucket:
- Branch: the branch containing this app
- Root directory: this project's folder (leave blank if repository root)
- Build command: `echo 'Static app; no build required'`
- Publish directory: `dist`
- No environment variables or backend service required

The interface can be public; access to the actual AI is controlled by your Ollama network/proxy. Never place server tokens in the static files or build-time environment variables. After deployment use the actual `https://…onrender.com` origin in OLLAMA_ORIGINS. Ollama itself runs on your server, separately from this static frontend.

## Coding workspace
Open **Coding** after connecting Ollama. Relay selects the first recognized coding model from the server's `/api/tags` list, retaining a previously chosen coding model while it remains installed. Recognized name families include Qwen Coder, DeepSeek Coder, Code Llama, StarCoder, CodeGemma, Codestral, Devstral, Granite Code, CodeQwen, WizardCoder, OpenCoder, Stable Code, and Replit Code. Detection uses model names, not a performance benchmark; custom aliases can be chosen manually in the model menu. After installing another model on the server, reconnect to reload the model list.

When no coding family is found, the tab clearly identifies the current fallback model. It does not download models. Chat and Coding have separate conversation histories, drafts, and model selections. Switching tabs restores your Chat model; switching is blocked during a response or connection check. Existing conversations remain in Chat. Coding requests receive a coding system instruction, and fenced code blocks have Copy buttons; generated code is displayed as text and is never executed by Relay.

Run `node tests/coding.test.cjs` from this directory for model-detection, tab-selection, fallback, legacy-history, and mocked request coverage. Live Ollama and browser/device behavior still need verification with a configured server.

## Device compatibility and security review

See [device/browser support and verification limits](COMPATIBILITY.md) and [the Coding red-team report](SECURITY-REVIEW-CODING.md). Install help is also available inside the app. Current major desktop and mobile browsers are the support target; physical operating-system testing is not claimed.

Run `node tests/coding.test.cjs`, `node tests/compat.test.cjs`, and `node tests/red-team-coding.cjs` for the 19 local behavior, compatibility, and adversarial cases.
