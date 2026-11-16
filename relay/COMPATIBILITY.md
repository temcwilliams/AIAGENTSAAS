# Relay device and browser support

Relay is a browser PWA, with no OS-specific executable, shell, file-system dependency, or code execution. It is designed for current Chrome, Edge, Firefox, and Safari on supported operating systems. This is a browser support target, not a claim that every OS/version or physical device was tested.

| Operating system | Browser use | Install path |
| --- | --- | --- |
| Windows | Current Chrome, Edge, Firefox | Chrome/Edge browser menu → Install app |
| macOS | Current Safari, Chrome, Edge, Firefox | Chrome/Edge Install; Safari File → Add to Dock on macOS Sonoma 14+ |
| Linux | Current Chrome/Chromium, Edge, Firefox where available | Chromium/Edge Install if offered; otherwise browser/bookmark |
| ChromeOS | Current Chrome | Install from Chrome; launch from launcher |
| Android | Current Chrome, Firefox, Edge or other compatible browser | Chrome → Add to Home screen → Install; other browsers vary |
| iOS / iPadOS | Current Safari; other compatible browsers | Safari Share → Add to Home Screen → Add; Open as Web App if offered |

Installation is optional. Firefox desktop and browsers without PWA installation can use the same chat/coding workspace as a normal web page. Embedded in-app browsers may not expose installation, streaming, clipboard, or offline support; open the URL in an updated standalone browser. Obsolete browsers, e-readers, consoles, and unsupported operating systems are not guaranteed.

## Runtime handling

- HTTPS is required for hosted PWA/offline/clipboard features. Ollama needs a reachable HTTPS endpoint and correct CORS settings regardless of client OS.
- Storage denial or exhaustion falls back to session memory with a visible warning. Chats in this mode disappear on reload/close; never assume private browsing keeps data permanently.
- Clipboard denial displays a message and leaves code selectable; no generated code is executed.
- IDs work without crypto.randomUUID. Network deadlines do not require AbortSignal.timeout and remain active through connection JSON parsing.
- Native dialogs have an open-attribute fallback. Modern dialogs remain the preferred experience.
- The viewport uses vh with a dvh enhancement; touch inputs avoid automatic iOS text zoom and provide larger controls. On touch devices Enter adds a line; use Send. Desktop Enter sends, Shift+Enter adds a line, and IME composition is respected.
- Install help is always available, even without beforeinstallprompt. Keyboard hints use Ctrl on non-Apple devices and Command on Apple devices.
- Offline shell caching is optional; AI responses always require the server. Fonts use local system/serif fallbacks and do not require third-party font requests.
- Streaming requires fetch response streams and TextDecoder. When unavailable, Relay gives an upgrade-browser message rather than pretending to generate a reply.

## Verification limits

Local Node VM tests cover model selection, tab behavior, malicious content, literal clipboard copying and denial, pending-connection guards, touch/desktop keyboard behavior, blocked/full storage, ID fallbacks, dialog fallbacks, and header/body deadlines. These are mocked browser APIs, not real Safari/Firefox/Chromium runs. Public Render asset checks verify publication only. Physical-device installation, real cross-browser layout/offline behavior, and live Ollama/proxy inference remain unverified.

## Foreground voice

Voice input uses SpeechRecognition/webkitSpeechRecognition when available. Safari/Chrome support depends on OS, language, settings, and recognition-service connectivity; do not infer support solely from browser name. Other browsers may lack the API. The app offers keyboard-dictation fallback and explicit errors. Browser speech recognition may process audio remotely. Speech playback uses speechSynthesis where available; read-aloud can be disabled. iOS may require a fresh tap to resume recognition/playback. Locking the phone or leaving the app stops the PWA voice session; no background listening support is claimed. Preference cookies do not change these restrictions.
