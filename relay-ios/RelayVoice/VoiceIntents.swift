import AppIntents

struct OpenRelayVoiceIntent: AppIntent {
    static let title: LocalizedStringResource = "Open Relay Voice"
    static let description = IntentDescription("Open the voice screen. Tap Start while unlocked to activate the microphone.")
    static let openAppWhenRun = true
    func perform() async throws -> some IntentResult {
        await MainActor.run { AppServices.shared.selectedTab = 0 }
        return .result()
    }
}

struct StopRelayVoiceIntent: AppIntent {
    static let title: LocalizedStringResource = "Stop Relay Voice"
    static let description = IntentDescription("End the active voice session and release the microphone.")
    static let openAppWhenRun = false
    func perform() async throws -> some IntentResult & ProvidesDialog {
        await MainActor.run { AppServices.shared.voice.stop() }
        return .result(dialog: "Relay voice session stopped.")
    }
}

struct RelayVoiceShortcuts: AppShortcutsProvider {
    static var appShortcuts: [AppShortcut] {
        AppShortcut(intent: OpenRelayVoiceIntent(), phrases: ["Open voice in \(.applicationName)"], shortTitle: "Open voice", systemImageName: "waveform")
        AppShortcut(intent: StopRelayVoiceIntent(), phrases: ["Stop voice in \(.applicationName)"], shortTitle: "Stop voice", systemImageName: "stop.circle")
    }
}
