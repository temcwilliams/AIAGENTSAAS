# Relay UI — quick independent red-team review

2026-11-16. Scope: bounded local source review and Chromium adversarial UI checks. No external services attacked, no production state changed, and no real microphone/audio or Ollama traffic used.

## Finding and hardening

**Low — overlays did not consistently cancel active voice.** Server settings and chat navigation explicitly stopped voice, while generic Install Help/privacy dialogs and opening the mobile drawer did not. A user could obscure the voice controls without explicitly ending the voice session. The owner added cancellation at the common dialog and drawer-opening entry points; the independent browser retest passed. This is privacy hardening based on the confirmed missing guards; automatic transmission behind an overlay was not reproduced. Deterministic controller-stub regression checks are provided to verify cancellation.

## Local browser checks

`node tests/red-team-ui.browser.cjs` uses Playwright and local Chromium against the local app at a 390 × 844 mobile viewport. Tests cover:

- Thirty keyboard-tab steps while the mobile drawer is open never focus main content; Escape restores main interactivity and makes the closed drawer inert.
- Twenty-five keyboard-tab steps inside the native settings dialog do not focus background controls. Browser chrome/body focus during native wrap is allowed. Escape closes the dialog and returns focus to its trigger.
- Markup and cookie-attribute payloads in preferences cannot inject DOM or create another cookie. Unsupported theme values fall back to dark; saving preferences keeps only the five allowed preference fields.
- A long mobile conversation scrolls inside the chat pane without outer-page horizontal/vertical overflow.
- Deterministic voice cancellation on opening Install Help, Cookies/privacy, and the mobile drawer (final retest status below).

Theme values are allowlisted; cookie values are encoded; token, URL, and chat payload keys are not retained by preference sanitization. Model names in the preference cookie are intentionally browser-owned preference data and are not authentication claims.

## Verification limits

This quick review does not establish universal accessibility or device compatibility. Native Chromium dialogs were tested, not legacy fallback implementations or physical phones. Voice cancellation regression uses a deterministic controller stub; real speech recognition, microphone permissions, and audio playback were not verified. The earlier owner-run four-viewport browser suite and 26 behavior/security tests are separate evidence, not additional tests executed by this reviewer in this pass.

Final overlay-hardening retest: **passed**, together with all four other browser check groups above. No additional confirmed issue remained in the bounded checks.
