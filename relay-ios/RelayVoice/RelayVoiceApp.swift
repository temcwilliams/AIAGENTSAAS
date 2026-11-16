import SwiftUI
import Observation

@MainActor @Observable
final class AppServices {
    static let shared = AppServices()
    var selectedTab = 0
    let voice = VoiceSession()
    let server = ServerStore()
}

@main @MainActor
struct RelayVoiceApp: App {
    @State private var services = AppServices.shared
    var body: some Scene {
        WindowGroup {
            RelayRootView(services: services)
                .onOpenURL { url in
                    if url.scheme == "relayvoice", url.host == "voice" { services.selectedTab = 0 }
                    // Deep links never activate the microphone or accept server credentials.
                }
        }
    }
}

@MainActor
struct RelayRootView: View {
    @Bindable var services: AppServices
    var body: some View {
        TabView(selection: $services.selectedTab) {
            NavigationStack { VoiceView(voice: services.voice, server: services.server) }
                .tabItem { Label("Voice", systemImage: "waveform") }.tag(0)
            NavigationStack { ServerView(server: services.server, voice: services.voice) }
                .tabItem { Label("Server", systemImage: "server.rack") }.tag(1)
            NavigationStack { VoiceHelpView() }
                .tabItem { Label("Guide", systemImage: "questionmark.circle") }.tag(2)
        }
        .tint(Color(red: 0.36, green: 0.42, blue: 0.29))
    }
}
