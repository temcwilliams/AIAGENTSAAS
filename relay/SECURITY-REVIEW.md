# Relay security review

Reviewed locally by an independent Team Red agent on 2026-11-16. Scope: browser source, connection state, token handling, DOM rendering, service-worker caching, and malicious streaming behavior. No external services were attacked. This is a bounded code review and adversarial mock test, not a certification or live deployment penetration test.

## Findings and remediation

- **Medium: pending connection could redirect chat history before validation. Fixed.** The original connection handler immediately replaced the active URL/token while retaining old models. A deferred-fetch test reproduced that state. The revised handler validates a local candidate, commits the connection atomically, and blocks chat submission while validation is pending. Retest confirmed the previous endpoint remains active until successful validation.
- **Low: unbounded streaming could exhaust browser memory. Fixed.** The revised implementation aborts responses over 4 MB, buffered records over 1 MB, and streams idle for 60 seconds. Local mocked streams verified both size limits abort and an accelerated idle timer cancels stalled reads.

## Other observations

No direct script injection path was found in chat text, model names, conversation titles, or connection errors: these use textContent. The limited innerHTML assignment contains only fixed application strings. Optional bearer tokens remain in memory and are not written to localStorage or the service-worker cache. The service worker caches only an explicit same-origin app-shell list and ignores cross-origin/API requests. Server URL validation rejects embedded credentials and requires HTTPS when hosted over HTTPS.

Conversations remain unencrypted in localStorage by design and are available to users of the same browser profile; private-site sign-in does not independently encrypt or clear that storage. Live Ollama authentication, reverse-proxy CORS, TLS, and remote access cannot be verified until the user's server exists. Browser installation and offline behavior were not exercised in this review.

## Verification performed

- Deferred-fetch VM test of connection state before and after successful validation.
- Oversized-record and total-byte-limit malicious stream tests.
- Accelerated idle-stream timeout test.
- Source inspection of DOM sinks, token persistence, and service-worker request selection.
