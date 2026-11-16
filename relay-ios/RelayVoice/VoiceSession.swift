import AVFoundation
import Speech
import Observation
import UIKit

// Audio callbacks are not on the main actor. Keep request handoff synchronized.
private final class AudioBridge: @unchecked Sendable {
    private let lock = NSLock()
    private var request: SFSpeechAudioBufferRecognitionRequest?
    func set(_ value: SFSpeechAudioBufferRecognitionRequest?) {
        lock.lock(); defer { lock.unlock() }; request = value
    }
    func append(_ buffer: AVAudioPCMBuffer) {
        lock.lock(); defer { lock.unlock() }; request?.append(buffer)
    }
}

@MainActor @Observable
final class VoiceSession: NSObject, AVSpeechSynthesizerDelegate {
    enum Phase: String { case stopped = "Ready", starting = "Requesting permission", listening = "Listening", thinking = "Thinking", speaking = "Speaking" }
    private(set) var phase: Phase = .stopped
    private(set) var transcript = ""
    private(set) var messages: [ChatMessage] = []
    private(set) var notice = "Start while unlocked. Lock-screen continuation is experimental until tested on your iPhone."
    var isActive: Bool { phase != .stopped }

    @ObservationIgnored private let engine = AVAudioEngine()
    @ObservationIgnored private let bridge = AudioBridge()
    @ObservationIgnored private let speaker = AVSpeechSynthesizer()
    @ObservationIgnored private let recognizer = SFSpeechRecognizer(locale: .current)
    @ObservationIgnored private var recognition: SFSpeechRecognitionTask?
    @ObservationIgnored private var request: SFSpeechAudioBufferRecognitionRequest?
    @ObservationIgnored private var turn: Task<Void, Never>?
    @ObservationIgnored private var silence: Task<Void, Never>?
    @ObservationIgnored private var rollover: Task<Void, Never>?
    @ObservationIgnored private var expiry: Task<Void, Never>?
    @ObservationIgnored private var connection: Connection?
    @ObservationIgnored private var sessionID = UUID()
    @ObservationIgnored private var recognitionID = UUID()
    @ObservationIgnored private var tapInstalled = false
    @ObservationIgnored private var emptyWindows = 0
    @ObservationIgnored private var observers: [NSObjectProtocol] = []

    override init() {
        super.init()
        speaker.delegate = self
        observers.append(NotificationCenter.default.addObserver(forName: AVAudioSession.interruptionNotification, object: nil, queue: .main) { [weak self] _ in
            Task { @MainActor in self?.stop("Audio interrupted. Unlock and start a new session when ready.") }
        })
        observers.append(NotificationCenter.default.addObserver(forName: AVAudioSession.routeChangeNotification, object: nil, queue: .main) { [weak self] note in
            let reason = note.userInfo?[AVAudioSessionRouteChangeReasonKey] as? UInt
            if reason == AVAudioSession.RouteChangeReason.oldDeviceUnavailable.rawValue {
                Task { @MainActor in self?.stop("Audio device disconnected. Start again to choose a new route.") }
            }
        })
    }

    func start(connection: Connection) async {
        guard !isActive, UIApplication.shared.applicationState == .active else { return }
        sessionID = UUID(); let id = sessionID
        phase = .starting
        do {
            guard !connection.model.isEmpty else { throw RelayError.message("Connect and select a model in Server first.") }
            let microphone = await withCheckedContinuation { continuation in
                AVAudioSession.sharedInstance().requestRecordPermission { continuation.resume(returning: $0) }
            }
            guard id == sessionID else { return }
            guard microphone else { throw RelayError.message("Allow microphone access in Settings to start voice.") }
            let speech = await withCheckedContinuation { continuation in
                SFSpeechRecognizer.requestAuthorization { continuation.resume(returning: $0) }
            }
            guard id == sessionID else { return }
            guard speech == .authorized else { throw RelayError.message("Allow Speech Recognition in Settings to start voice.") }
            guard let recognizer, recognizer.isAvailable, recognizer.supportsOnDeviceRecognition else {
                throw RelayError.message("On-device speech recognition is unavailable for this device/language. No audio was sent to cloud recognition.")
            }
            let audio = AVAudioSession.sharedInstance()
            try audio.setCategory(.playAndRecord, mode: .voiceChat, options: [.defaultToSpeaker, .allowBluetooth])
            try audio.setActive(true)
            let input = engine.inputNode
            let format = input.outputFormat(forBus: 0)
            guard format.sampleRate > 0, format.channelCount > 0 else { throw RelayError.message("No usable microphone found.") }
            let bridge = self.bridge
            input.installTap(onBus: 0, bufferSize: 1024, format: format) { buffer, _ in bridge.append(buffer) }
            tapInstalled = true
            engine.prepare(); try engine.start()
            self.connection = connection
            emptyWindows = 0
            notice = "Voice session active. Speech stays on-device; transcribed text goes to your Ollama server. Stop ends microphone access."
            listen()
            expiry = Task { [weak self] in
                try? await Task.sleep(for: .seconds(1800))
                guard !Task.isCancelled, self?.sessionID == id else { return }
                self?.stop("Session ended after 30 minutes. Start again when ready.")
            }
        } catch { if id == sessionID { stop(error.localizedDescription) } }
    }

    func stop(_ reason: String = "Voice session stopped. The microphone is off.") {
        sessionID = UUID()
        turn?.cancel(); turn = nil
        expiry?.cancel(); expiry = nil
        endRecognition()
        speaker.stopSpeaking(at: .immediate)
        engine.stop()
        if tapInstalled { engine.inputNode.removeTap(onBus: 0); tapInstalled = false }
        try? AVAudioSession.sharedInstance().setActive(false, options: .notifyOthersOnDeactivation)
        connection = nil
        phase = .stopped; notice = reason
    }

    func clear() { stop(); messages.removeAll(); transcript = "" }

    private func endRecognition() {
        recognitionID = UUID()
        silence?.cancel(); silence = nil
        rollover?.cancel(); rollover = nil
        bridge.set(nil)
        request?.endAudio(); request = nil
        recognition?.cancel(); recognition = nil
    }

    private func listen() {
        guard isActive, let recognizer, engine.isRunning else { return }
        endRecognition(); transcript = ""; phase = .listening
        let id = recognitionID
        let request = SFSpeechAudioBufferRecognitionRequest()
        request.requiresOnDeviceRecognition = true
        request.shouldReportPartialResults = true
        self.request = request
        bridge.set(request)
        recognition = recognizer.recognitionTask(with: request) { [weak self] result, error in
            let text = result?.bestTranscription.formattedString
            let final = result?.isFinal ?? false
            let failure = error?.localizedDescription
            Task { @MainActor in
                guard let self, self.recognitionID == id, self.phase == .listening else { return }
                if let text, !text.isEmpty {
                    self.transcript = String(text.prefix(8_000))
                    self.silence?.cancel()
                    if final { self.submit() }
                    else {
                        self.silence = Task { [weak self] in
                            try? await Task.sleep(for: .milliseconds(1600))
                            guard !Task.isCancelled, self?.recognitionID == id else { return }
                            self?.submit()
                        }
                    }
                } else if let failure { self.stop("Speech recognition stopped: \(failure). Unlock and restart the session.") }
            }
        }
        rollover = Task { [weak self] in
            try? await Task.sleep(for: .seconds(45))
            guard !Task.isCancelled, let self, self.recognitionID == id else { return }
            if self.transcript.isEmpty {
                self.emptyWindows += 1
                if self.emptyWindows >= 6 { self.stop("Session ended after several minutes without speech.") }
                else { self.listen() }
            } else { self.submit() }
        }
    }

    private func submit() {
        guard phase == .listening, let connection else { return }
        let text = transcript.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty else { return }
        endRecognition(); emptyWindows = 0; phase = .thinking
        messages.append(ChatMessage(role: "user", content: text))
        let id = sessionID
        turn = Task { [weak self] in
            guard let self else { return }
            do {
                let reply = try await OllamaClient().reply(self.messages, connection: connection)
                guard !Task.isCancelled, self.sessionID == id else { return }
                self.messages.append(ChatMessage(role: "assistant", content: reply))
                if self.messages.count > 100 { self.messages.removeFirst(self.messages.count - 100) }
                self.phase = .speaking
                let utterance = AVSpeechUtterance(string: reply)
                utterance.voice = AVSpeechSynthesisVoice(language: Locale.current.identifier.replacingOccurrences(of: "_", with: "-"))
                self.speaker.speak(utterance)
            } catch { if !Task.isCancelled, self.sessionID == id { self.stop(error.localizedDescription) } }
        }
    }

    nonisolated func speechSynthesizer(_ synthesizer: AVSpeechSynthesizer, didFinish utterance: AVSpeechUtterance) {
        Task { @MainActor [weak self] in guard let self, self.phase == .speaking else { return }; self.listen() }
    }
}
