# Relay Coding — independent red-team review

Date: 2026-11-16. Scope: local source and mocked adversarial tests of Relay's Coding workspace and browser-compatibility changes. No external services were attacked. These results are a bounded code review and regression suite, not a live penetration test or security certification.

## Findings

1. **Low — Demo could be overridden by an in-flight connection. Fixed and retested.** Choosing Demo while `/api/tags` was pending displayed a promise that no requests would be sent, but the late successful connection restored live models. The application now disables/refuses Demo during connection validation or an active response. The regression verifies refusal, completion of the intentional live connection, then successful entry into Demo.
2. **Low — model-list response body could stall indefinitely. Fixed and retested.** The first compatibility timeout wrapper cleared its deadline after headers arrived. A stalled JSON body then left connection validation active indefinitely, blocking chat and mode switching. The wrapper now awaits the JSON consumer inside the deadline. A fake-timer adversarial test confirms the deadline remains active after headers; the compatibility suite also verifies timeout cancellation of a stalled body.

No additional confirmed security vulnerability remains from the tested cases.

## Adversarial checks

`node tests/red-team-coding.cjs`: **8 passed**.

- HTML/script/event-handler payloads in prose, fence language labels, and code create only inert text in the mock DOM. No raw payload reaches an HTML parser or an executable element.
- Code is copied only after explicit button activation, preserving literal content; clipboard denial is handled without execution or content mutation.
- Unrelated model tags and markup do not spoof the recognized coding-family detector or inject DOM. A deliberately renamed model such as `untrusted/coder:latest` remains recognizable by design: model names are a heuristic, not authenticated capability metadata.
- Pending server validation blocks both chat submission and mode switching and preserves the previous endpoint until validation succeeds.
- Demo cannot claim to disable live requests while validation is pending.
- The service worker includes the coding routing module and ignores API, cross-origin, mutation, and sign-out requests.
- A connection deadline remains active during stalled model-list JSON reads.
- Denied localStorage and missing newer UUID/AbortSignal APIs do not prevent demo startup and chat creation; the UI identifies session-only storage.

Supporting suites rerun unchanged: `node tests/coding.test.cjs` **5 passed** and `node tests/compat.test.cjs` **6 passed**. Total: **19 passing tests**.

## Limits and operating assumptions

- Tests use a mock DOM, fetch responses, timers, and browser APIs. Real browser parsing, layout, installation, offline recovery, and clipboard permissions were not exercised here.
- Physical OS/device testing on Windows, macOS, Linux, ChromeOS, Android, iPhone, and iPad was unavailable. Compatibility fallbacks are implemented and unit tested; universal device compatibility has not been established.
- Live Ollama inference, proxy authentication, HTTPS, CORS, and remote reachability remain unverified until the user's server is configured.
- Model output is untrusted code. Relay displays/copies it but does not run commands or edit repositories. Copying a command does not establish that it is safe to execute elsewhere.
- Conversations remain unencrypted in browser storage by design. Users sharing a browser profile can access them. Bearer tokens remain in memory rather than localStorage.
