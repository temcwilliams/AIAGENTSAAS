import Foundation
import Observation

@MainActor @Observable
final class ServerStore {
    var address = UserDefaults.standard.string(forKey: "voice-server-address") ?? ""
    var token = "" // Session memory only; never written to defaults or logs.
    var model = UserDefaults.standard.string(forKey: "voice-server-model") ?? ""
    private(set) var models: [String] = []
    private(set) var loading = false
    private(set) var status = "Connect your HTTPS Ollama server."
    private var validated: Connection?
    var connection: Connection? {
        guard let validated, models.contains(model) else { return nil }
        return try? Connection(address: validated.baseURL.absoluteString, model: model, token: validated.token)
    }
    func connect() async {
        guard !loading else { return }
        loading = true; status = "Checking installed models…"
        defer { loading = false }
        do {
            let candidate = try Connection(address: address, model: "", token: token)
            let installed = try await OllamaClient().models(candidate)
            guard !installed.isEmpty else { throw RelayError.message("No models installed. Pull a model on your server first.") }
            validated = candidate; models = installed
            if !installed.contains(model) { model = installed[0] }
            UserDefaults.standard.set(candidate.baseURL.absoluteString, forKey: "voice-server-address")
            status = "Connected. Changes to address or token apply after reconnecting."
        } catch { status = error.localizedDescription }
    }
    func rememberModel() { UserDefaults.standard.set(model, forKey: "voice-server-model") }
}
