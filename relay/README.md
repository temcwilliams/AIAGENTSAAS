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

## PWA voice and preference cookies

No App Store or Xcode is required for the PWA. Connect Ollama, tap **Start voice**, read the browser-recognition notice, then explicitly start the conversation. Where browser speech recognition is available, recognized words are submitted to Ollama; completed replies can be read aloud, then listening resumes. Stop, navigation, page hiding, or errors end voice. Pending voice requests are aborted on Stop and stale callbacks cannot resume listening. No microphone activation occurs automatically on page load or from cookies. Speech input may use the browser vendor's recognition service; this is not an on-device privacy guarantee. Unsupported browsers can use keyboard dictation.

Voice is foreground-only. Cookies do not enable locked-screen/background microphone access or Siri wake words. Browser/device voice and physical iPhone behavior are unverified; the native project remains separate historical source, not the active PWA deployment path.

The `relay_preferences` first-party cookie stores only tab, Chat/Coding model names, theme, and read-aloud preference. It has a 180-day Max-Age, Path=/, SameSite=Strict and Secure on HTTPS; no Domain attribute is set. It is a JavaScript-readable preference cookie, not an authentication/session cookie. Chat messages and proxy tokens are excluded. Chat history/server address remain localStorage and token remains memory-only. **Cookies & privacy** explains this and resets the cookie. Blocked or malformed cookies fall back safely to in-memory defaults. Preferences do not sync devices.

Run `node tests/voice.test.cjs` alongside the earlier suites (26 local cases in total). Voice integration uses browser APIs and requires real-device checks for permissions, provider availability, speech synthesis user-activation rules, and background suspension.

## Appearance, menus, and scrolling

Relay opens with a navy/cyan dark theme. The header theme button switches to light mode and remembers the choice in the preference cookie. The sidebar profile button also switches themes. The theme uses real colors and native control color schemes rather than a page-wide inversion filter.

On mobile, close navigation with ×, a backdrop tap, Escape, or choosing a destination. Closed navigation is inert; opening it makes the background workspace inert. Dialogs have sticky close controls, outside-click/Escape dismissal, reset scroll when reopened, and close any previous dialog. Initial focus goes to Close so opening settings does not immediately summon a mobile keyboard.

The welcome screen fits the checked desktop/phone sizes without page or chat overflow. Long conversations and code retain scrolling inside their content areas; the composer stays in view. Decorative scrollbars are hidden in the conversation and history regions.

Browser regressions: start a static server for `dist` (e.g. `python -m http.server 4173 --directory dist` from `relay/`). With Playwright and its Chromium installed in your development environment, run `node tests/ui.browser.cjs`. `RELAY_TEST_URL` selects another URL, and `RELAY_BROWSER_EXECUTABLE` selects an existing Chromium binary. The suite checks four viewport sizes, theme persistence, drawer dismissal/inert state, all four dialogs, close visibility after scrolling, one-modal-at-a-time behavior, and long-chat layout. Physical Safari/iPhone verification is still pending.

## Composer behavior

Send is enabled only for nonblank drafts when no response/connection is in progress. A separate Stop button cancels the active reply. The input stays editable while a reply is running; Enter then preserves the draft rather than aborting the response. Desktop Enter sends when ready, Shift+Enter adds a line; touch keyboards keep Enter for newlines and use Send. IME composition events (including keyCode 229) never trigger submission. Typed drafts cannot be replaced by a late browser-voice result. Text input grows to a bounded height and then scrolls internally; clearing/submitting resets its size.

`node tests/composer.browser.cjs` (same Playwright/server setup as the UI suite) checks sending, empty drafts, separate cancellation, follow-up draft retention, composition, multiline input, failed-response recovery, voice/draft collision, and bounded long text at desktop, tablet, and two phone sizes with mocked Ollama responses. Real Ollama and physical device keyboards remain unverified.
