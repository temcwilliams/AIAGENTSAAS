import SwiftUI

@MainActor
struct VoiceView: View {
    let voice: VoiceSession
    let server: ServerStore
    var body: some View {
        VStack(spacing: 16) {
            VStack(spacing: 10) {
                Image(systemName: voice.isActive ? "waveform.circle.fill" : "mic.circle")
                    .font(.system(size: 64)).foregroundStyle(voice.isActive ? Color.green : Color.secondary)
                    .accessibilityHidden(true)
                Text(voice.phase.rawValue).font(.title2.bold()).accessibilityAddTraits(.updatesFrequently)
                Text(voice.notice).font(.footnote).foregroundStyle(.secondary).multilineTextAlignment(.center)
                if !voice.transcript.isEmpty { Text(voice.transcript).font(.callout).lineLimit(4) }
            }.padding(.horizontal)
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 16) {
                    ForEach(voice.messages) { message in
                        VStack(alignment: .leading, spacing: 4) {
                            Text(message.role == "user" ? "YOU" : "RELAY").font(.caption.bold()).foregroundStyle(.secondary)
                            Text(message.content).textSelection(.enabled)
                        }.padding().frame(maxWidth: .infinity, alignment: .leading)
                            .background(message.role == "user" ? Color.green.opacity(0.08) : Color.secondary.opacity(0.06), in: RoundedRectangle(cornerRadius: 14))
                    }
                }.padding(.horizontal)
            }
            if voice.isActive {
                Button(role: .destructive) { voice.stop() } label: { Label("Stop voice session", systemImage: "stop.fill").frame(maxWidth: .infinity) }
                    .buttonStyle(.borderedProminent).accessibilityIdentifier("stopVoice")
            } else {
                Button {
                    guard let connection = server.connection else { return }
                    Task { await voice.start(connection: connection) }
                } label: { Label("Start voice session", systemImage: "mic.fill").frame(maxWidth: .infinity) }
                    .buttonStyle(.borderedProminent).disabled(server.connection == nil || server.loading)
                    .accessibilityIdentifier("startVoice")
            }
            if server.connection == nil { Text("Connect and select a model in Server first.").font(.caption).foregroundStyle(.secondary) }
        }.padding().navigationTitle("Relay Voice")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Clear", systemImage: "trash") { voice.clear() }.disabled(voice.messages.isEmpty && !voice.isActive)
                }
            }
    }
}

@MainActor
struct ServerView: View {
    @Bindable var server: ServerStore
    let voice: VoiceSession
    var body: some View {
        Form {
            Section("Your Ollama server") {
                TextField("https://ai.example.com", text: $server.address)
                    .textInputAutocapitalization(.never).autocorrectionDisabled().keyboardType(.URL)
                SecureField("Proxy token (session only)", text: $server.token)
                    .textInputAutocapitalization(.never).autocorrectionDisabled()
                Button(server.loading ? "Connecting…" : "Connect & load models") { Task { await server.connect() } }
                    .disabled(server.loading)
                if !server.models.isEmpty {
                    Picker("Model", selection: $server.model) {
                        ForEach(server.models, id: \.self) { Text($0).tag($0) }
                    }.onChange(of: server.model) { _, _ in server.rememberModel() }
                }
                Text(server.status).font(.footnote).foregroundStyle(.secondary)
            }.disabled(voice.isActive)
            Section("Privacy") {
                Text("Speech recognition runs on-device when supported. Only transcribed text is sent to your server. Raw audio is not saved. Conversations and proxy tokens are kept in memory until cleared or the app exits.")
                Text("The server address and selected model are remembered on this device. Reconnect after relaunch and re-enter your proxy token.")
            }
            if voice.isActive { Text("Stop the voice session before changing servers or models.") }
        }.navigationTitle("Server")
    }
}

struct VoiceHelpView: View {
    var body: some View {
        List {
            Section("Start a conversation") {
                Text("Connect Ollama in Server, allow Microphone and Speech Recognition, then tap Start while the app is unlocked. Speak naturally; a short pause sends your words. Relay speaks its reply, then listens again.")
            }
            Section("Lock-screen sessions — experimental") {
                Text("Background audio is configured so an active voice session can continue when the screen locks. On-device speech availability and background behavior must be verified on your iPhone. If iOS interrupts recognition, unlock and restart. This does not provide a system-wide wake word or replace Siri.")
                Text("Use headphones to reduce feedback. Relay does not listen for the next turn while speaking. Stop ends microphone access; disconnecting an audio device or receiving an interruption also stops the session. Sessions expire after 30 minutes or several minutes without speech.")
            }
            Section("Siri and Shortcuts") {
                Text("After installing, add Open Relay Voice in Shortcuts or say ‘Open voice in Relay Voice’. It opens this screen; unlock and tap Start to begin recording. Stop Relay Voice is also available in Shortcuts. Microphone permissions and system authentication still apply.")
            }
            Section("Connect anywhere") {
                Text("Keep Ollama behind authenticated HTTPS or a private VPN. Do not expose its unauthenticated port publicly. This native client has separate settings and conversation memory from the PWA.")
                Link("Open Relay web workspace", destination: URL(string: "https://relay-ollama.onrender.com")!)
            }
        }.navigationTitle("Voice guide")
    }
}
