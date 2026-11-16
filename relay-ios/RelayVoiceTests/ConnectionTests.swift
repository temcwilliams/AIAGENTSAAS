import XCTest
@testable import RelayVoice

final class ConnectionTests: XCTestCase {
    func testRejectsInsecureOrCredentialBearingAddresses() {
        for address in ["http://ai.example.com", "https://user:secret@ai.example.com", "https://ai.example.com?token=secret", "https://ai.example.com#token"] {
            XCTAssertThrowsError(try Connection(address: address, model: "llama3.2", token: ""))
        }
    }
    func testAcceptsHTTPSWithProxyPrefix() throws {
        let value = try Connection(address: " https://ai.example.com/ollama ", model: "llama3.2", token: "session")
        XCTAssertEqual(value.baseURL.appendingPathComponent("api/tags").absoluteString, "https://ai.example.com/ollama/api/tags")
    }
    func testMessageWireFormatDoesNotIncludeLocalIdentifier() throws {
        let message = ChatMessage(role: "user", content: "Hello")
        let object = try XCTUnwrap(JSONSerialization.jsonObject(with: JSONEncoder().encode(message)) as? [String: String])
        XCTAssertEqual(object, ["role": "user", "content": "Hello"])
        let decoded = try JSONDecoder().decode(ChatMessage.self, from: JSONEncoder().encode(message))
        XCTAssertEqual(decoded.content, "Hello")
    }
}
