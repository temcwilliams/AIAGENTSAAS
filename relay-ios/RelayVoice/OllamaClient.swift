import Foundation

struct Connection: Sendable {
    let baseURL: URL
    let model: String
    let token: String

    init(address: String, model: String, token: String) throws {
        guard let parts = URLComponents(string: address.trimmingCharacters(in: .whitespacesAndNewlines)),
              parts.scheme == "https", parts.host != nil,
              parts.user == nil, parts.password == nil, parts.query == nil, parts.fragment == nil,
              let url = parts.url else {
            throw RelayError.message("Enter an HTTPS base URL without credentials, query, or fragment.")
        }
        baseURL = url
        self.model = model
        self.token = token
    }
}

enum RelayError: LocalizedError {
    case message(String)
    var errorDescription: String? { if case .message(let text) = self { return text }; return nil }
}

struct ChatMessage: Codable, Identifiable, Sendable {
    var id = UUID()
    let role: String
    let content: String
    enum CodingKeys: String, CodingKey { case role, content }
}

struct OllamaClient: Sendable {
    private struct Tags: Decodable {
        struct Model: Decodable { let name: String }
        let models: [Model]
    }
    private struct Reply: Decodable { let message: ChatMessage }
    private struct Request: Encodable {
        let model: String
        let messages: [ChatMessage]
        let stream = false
        let options = ["num_predict": 256]
    }

    func models(_ connection: Connection) async throws -> [String] {
        let data = try await request(connection, path: "api/tags", body: nil)
        return try JSONDecoder().decode(Tags.self, from: data).models.map(\.name)
    }

    func reply(_ messages: [ChatMessage], connection: Connection) async throws -> String {
        guard !connection.model.isEmpty else { throw RelayError.message("Choose an installed model first.") }
        let system = ChatMessage(role: "system", content: "You are Relay, a helpful voice assistant. Reply concisely in plain spoken language. Do not claim to access apps, execute code, or perform actions. Avoid long code blocks unless requested.")
        let body = try JSONEncoder().encode(Request(model: connection.model, messages: [system] + Array(messages.suffix(16))))
        let data = try await request(connection, path: "api/chat", body: body)
        let text = try JSONDecoder().decode(Reply.self, from: data).message.content.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty else { throw RelayError.message("The model returned an empty reply.") }
        return String(text.prefix(12_000))
    }

    private func request(_ connection: Connection, path: String, body: Data?) async throws -> Data {
        var request = URLRequest(url: connection.baseURL.appendingPathComponent(path))
        request.timeoutInterval = 90
        request.httpMethod = body == nil ? "GET" : "POST"
        request.httpBody = body
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        if !connection.token.isEmpty { request.setValue("Bearer \(connection.token)", forHTTPHeaderField: "Authorization") }
        let config = URLSessionConfiguration.ephemeral
        config.timeoutIntervalForRequest = 90
        config.timeoutIntervalForResource = 120
        config.httpCookieStorage = nil
        config.urlCache = nil
        let session = URLSession(configuration: config, delegate: SameOriginRedirects(), delegateQueue: nil)
        defer { session.invalidateAndCancel() }
        let (bytes, response) = try await session.bytes(for: request)
        guard let http = response as? HTTPURLResponse, (200..<300).contains(http.statusCode) else {
            throw RelayError.message("Ollama rejected the request. Check the address, proxy token, and server.")
        }
        var data = Data()
        for try await byte in bytes {
            try Task.checkCancellation()
            guard data.count < 4 * 1024 * 1024 else { throw RelayError.message("Server response exceeded 4 MB.") }
            data.append(byte)
        }
        return data
    }
}

private final class SameOriginRedirects: NSObject, URLSessionTaskDelegate, @unchecked Sendable {
    func urlSession(_ session: URLSession, task: URLSessionTask,
                    willPerformHTTPRedirection response: HTTPURLResponse,
                    newRequest request: URLRequest,
                    completionHandler: @escaping (URLRequest?) -> Void) {
        // Reject redirects entirely: proxy credentials and transcripts stay at the configured endpoint.
        completionHandler(nil)
    }
}
