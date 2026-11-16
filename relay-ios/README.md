# Relay Voice — native iPhone/iPad companion

An iOS 17+ SwiftUI app, separate from the Relay PWA and Agent Meadow service. Uses Apple's Speech and AVFoundation frameworks plus the user's HTTPS Ollama server. No paid model API or third-party Swift dependency. Native app source was authored with the Build iOS Apps plugin's SwiftUI, debugging, and App Intents guidance.

## Implemented source

- User-started voice session with microphone and speech permissions.
- On-device speech recognition only, gated by `supportsOnDeviceRecognition`; no silent fallback to cloud recognition.
- Short pauses submit transcribed text to Ollama, then AVSpeechSynthesizer reads replies aloud and listening resumes.
- `playAndRecord` audio session and `UIBackgroundModes: audio` for an active session that may continue under screen lock. This is experimental until verified on a physical device. Apple may interrupt recognition; the app stops and requests restart rather than claiming it still listens.
- No system-wide wake word, no Siri replacement, no always-on recording at launch, no automatic microphone activation from a link or intent.
- Siri/App Shortcuts: Open Relay Voice and Stop Relay Voice. Opening routes to Voice; unlock and tap Start. Shortcuts do not bypass system authentication or microphone permission.
- Stop/Clear releases the microphone and cancels pending network, recognition, and playback work. Audio interruption/device disconnection stops the session. Empty listening windows and a 30-minute session cap limit unattended use.
- HTTPS-only server settings and model discovery; credentials/query fragments in the server URL rejected. Proxy token kept only in memory. Requests use an ephemeral no-cache session, reject redirects, bound response bytes, and enforce request/resource deadlines. Server edits apply only after successful reconnect; settings are disabled during a voice session.
- Conversation history is memory-only and separate from the PWA. No audio files are saved; transcribed messages go to the configured server when you speak during a session. The app's transcript is not hidden/encrypted merely because the screen is locked.

## Build and install on a Mac

1. Install Xcode with an iOS 17+ SDK and the simulator components. Install XcodeGen (`brew install xcodegen`).
2. From `relay-ios`, run `xcodegen generate`, then open `RelayVoice.xcodeproj`.
3. In Signing & Capabilities, select your Apple development team and a unique bundle identifier. The example ID is not a registered production app ID. Review the Audio background capability and microphone/speech usage descriptions.
4. Connect your iPhone, enable Developer Mode if requested, choose it in Xcode, then Run. Personal development signing can be used within Apple's limits; TestFlight/App Store distribution requires the corresponding Apple developer setup and review. No certificate, profile, or account credential is included here.
5. Enter your reachable HTTPS Ollama base URL, proxy token if needed, connect and choose an installed model. Use a private VPN or authenticated reverse proxy; never expose bare Ollama publicly.
6. Tap Start while unlocked, grant permissions, and test a foreground turn before attempting lock-screen use.

GitHub workflow `Relay iOS` generates the project, builds without signing for Simulator, and runs connection/wire-format unit tests on a macOS runner. A successful simulator build is not a signed iPhone installation or evidence that background speech recognition works under lock.

## Physical-device acceptance checks (pending)

- Fresh install: deny/grant permissions; unsupported on-device language must show an explicit error and never send audio to remote recognition.
- Real Ollama: successful model list, token rejection, missing model, slow network, VPN disconnect, and server response limits; no credentials/transcripts in logs.
- Speak one turn, hear response, then another turn. Verify output isn't transcribed back into the next prompt. Long pauses, long utterances, and recognition rollover must not duplicate submissions.
- Start foreground, lock screen, speak multiple turns over several minutes, then unlock. Repeat with wired/Bluetooth headphones, speaker, Low Power Mode, Wi-Fi/mobile transitions, and actual target iOS version. If recognition stops while locked, this release does not meet background-voice acceptance; investigate a supported on-device speech engine or explicit server transcription before claiming support.
- Phone/alarm interruptions, headphones unplugged, Stop intent, manual Stop, app termination, idle expiry: microphone must release and no late model response should speak.
- Siri shortcut opens Voice correctly, requires any system authentication, and never starts listening by itself. Test Stop while an active session is running.

## Reference basis

[Apple playAndRecord](https://developer.apple.com/documentation/avfaudio/avaudiosession/category-swift.struct/playandrecord), [on-device recognition support](https://developer.apple.com/documentation/speech/sfspeechrecognizer/supportsondevicerecognition), [requiresOnDeviceRecognition](https://developer.apple.com/documentation/speech/sfspeechrecognitionrequest/requiresondevicerecognition), and [App Intents](https://developer.apple.com/documentation/appintents/creating-your-first-app-intent).

## Verification status

This Linux authoring workspace has neither Xcode nor Swift nor the plugin's XcodeBuildMCP tools. Local source/configuration checks can run here; native compilation is delegated to the repository's macOS CI. Physical iPhone installation and lock-screen operation remain unverified until completed with Apple signing and real hardware. The existing PWA/Render services are not redeployed by native-only source changes.
