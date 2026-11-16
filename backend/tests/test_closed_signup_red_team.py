"""Local bypass attempts against owner-provisioned account access only."""
import json

from sqlalchemy import func, select

from app.config import settings
from app.db import get_db
from app.main import app
from app.models import Business, Session, User
from app.security import digest, verify
from conftest import login


def test_retired_signup_rejects_encoded_paths_transports_and_privileged_session(setup, monkeypatch):
    client, _ = setup
    assert login(client).status_code == 200
    admin_cookie = client.cookies.get("session")
    monkeypatch.setattr(settings, "owner_setup_token_hash", digest("local-retired-owner-code"))
    payload = {"email": "bypass@example.com", "password": "Test-password-123!", "business_name": "Bypass", "setup_token": "local-retired-owner-code", "role": "admin"}

    def forbidden_database():
        raise AssertionError("Retired signup must not depend on database authorization or availability")

    def forbidden_hash(*args, **kwargs):
        raise AssertionError("Retired signup must never perform password work")

    app.dependency_overrides[get_db] = forbidden_database
    monkeypatch.setattr("app.security.hasher.hash", forbidden_hash)
    transports = [
        {"content": json.dumps(payload), "headers": {"Content-Type": "text/plain"}},
        {"data": payload},
        {"files": {key: (None, value) for key, value in payload.items()}},
    ]
    for path in ("/auth/register", "/auth/register/", "/auth/%72egister"):
        for transport in transports:
            response = client.post(path + "?setup_token=local-retired-owner-code&role=admin", **transport)
            assert response.status_code == 403
            assert "disabled" in response.json()["detail"]
            assert "set-cookie" not in response.headers
            assert client.cookies.get("session") == admin_cookie
    for method in ("GET", "PUT", "PATCH", "DELETE"):
        response = client.request(method, "/auth/register", headers={"X-HTTP-Method-Override": "POST"}, content=json.dumps(payload))
        assert response.status_code == 405


def test_client_cannot_provision_accounts_using_spoofed_claims_or_method_overrides(setup):
    client, factory = setup
    assert login(client, "a@example.com").status_code == 200
    with factory() as database:
        counts = [database.scalar(select(func.count()).select_from(model)) for model in (User, Business, Session)]
    headers = {"X-User-Role": "admin", "X-Business-ID": "b", "X-HTTP-Method-Override": "POST", "Authorization": "Bearer forged-admin-claim"}
    response = client.post("/users/", headers=headers, json={"email": "bypass@example.com", "password": "Test-password-123!", "business_id": "b", "role": "admin", "is_admin": True})
    assert response.status_code == 403
    response = client.post("/businesses/", headers=headers, json={"name": "Unauthorized business", "owner_id": "self", "role": "admin"})
    assert response.status_code == 403
    assert client.put("/businesses/b", headers=headers, json={"name": "Hijacked"}).status_code == 403
    with factory() as database:
        assert [database.scalar(select(func.count()).select_from(model)) for model in (User, Business, Session)] == counts
        assert database.get(Business, "b").name == "Beta"


def test_operator_provisioning_cannot_overpost_an_admin_or_session(setup):
    client, factory = setup
    assert login(client).status_code == 200
    original_session = client.cookies.get("session")
    payload = {"email": "approved@example.com", "password": "Approved-password-123!", "business_id": "a", "role": "admin", "is_admin": True, "id": "attacker-selected-id", "password_hash": "attacker-selected-hash", "session": "attacker-selected-session", "setup_token": "retired-code"}
    response = client.post("/users", json=payload)
    assert response.status_code == 201
    assert set(response.json()) == {"id", "email"}
    assert "set-cookie" not in response.headers
    assert client.cookies.get("session") == original_session
    with factory() as database:
        created = database.get(User, response.json()["id"])
        assert created.role == "client" and created.business_id == "a"
        assert created.id != "attacker-selected-id"
        assert verify(payload["password"], created.password_hash)
        assert database.get(Session, digest("attacker-selected-session")) is None
    assert client.post("/auth/logout").status_code == 204
    assert client.post("/auth/login", json={"email": payload["email"], "password": payload["password"], "role": "admin"}).status_code == 200
    assert client.get("/auth/me").json()["role"] == "client"
    assert client.get("/businesses/b/floor").status_code == 404
    assert client.post("/users", json={"email": "next@example.com", "password": payload["password"], "business_id": "a"}).status_code == 403

