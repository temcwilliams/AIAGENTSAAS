"""Bounded, local adversarial checks. No production traffic or real model calls."""
import json
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from sqlalchemy.orm import Session as DBSession
from sqlalchemy import select, func
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import OperationalError
from fastapi import HTTPException

from app.config import settings
from app.security import DUMMY_HASH, BoundedPasswordHasher, digest
from app.db import locked_scalar
from app.models import Conversation, RateLimitBucket
from conftest import login
from test_api import AGENT


def test_empty_conversation_creation_budget_is_shared_and_ownership_checked_first(setup, monkeypatch):
    client, factory = setup
    monkeypatch.setattr(settings, "conversations_per_hour", 2)
    assert login(client).status_code == 200
    alpha_agents = [client.post("/businesses/a/agents", json=AGENT).json()["id"] for _ in range(2)]
    beta_agent = client.post("/businesses/b/agents", json=AGENT).json()["id"]
    assert login(client, "a@example.com").status_code == 200
    assert client.post("/businesses/a/agents/missing/conversations").status_code == 404
    assert client.post(f"/businesses/a/agents/{beta_agent}/conversations").status_code == 404
    assert client.post(f"/businesses/b/agents/{beta_agent}/conversations").status_code == 404
    with factory() as database:
        assert database.get(RateLimitBucket, digest("conversation-create:a")) is None
        assert database.get(RateLimitBucket, digest("conversation-create:b")) is None
    assert client.post(f"/businesses/a/agents/{alpha_agents[0]}/conversations").status_code == 201
    assert login(client).status_code == 200
    assert client.post(f"/businesses/a/agents/{alpha_agents[1]}/conversations").status_code == 201
    denied = client.post(f"/businesses/a/agents/{alpha_agents[0]}/conversations")
    assert denied.status_code == 429 and denied.headers["retry-after"] == "3600"
    # One tenant exhausting its budget cannot consume another tenant's budget.
    assert client.post(f"/businesses/b/agents/{beta_agent}/conversations").status_code == 201
    with factory() as database:
        assert database.scalar(select(func.count(Conversation.id)).where(Conversation.business_id == "a")) == 2
        assert database.scalar(select(func.count(Conversation.id)).where(Conversation.business_id == "b")) == 1
        assert database.get(RateLimitBucket, digest("conversation-create:a")).count == 2


def test_conversation_lock_query_uses_postgres_nowait_and_refreshes_state():
    sentinel = object()
    database = SimpleNamespace(scalar=Mock(return_value=sentinel), rollback=Mock())
    query = select(Conversation).where(Conversation.id == "conversation", Conversation.business_id == "tenant")
    assert locked_scalar(database, query) is sentinel
    statement = database.scalar.call_args.args[0]
    compiled = str(statement.compile(dialect=postgresql.dialect()))
    assert "FOR UPDATE NOWAIT" in compiled
    assert "conversations.business_id" in compiled
    assert statement.get_execution_options()["populate_existing"] is True
    database.rollback.assert_not_called()


@pytest.mark.parametrize("sqlstate", ["55P03", "08006"])
def test_only_lock_contention_is_translated_to_retryable_conflict(sqlstate):
    original = Exception("simulated database error")
    original.sqlstate = sqlstate
    error = OperationalError("SELECT", {}, original)
    database = SimpleNamespace(scalar=Mock(side_effect=error), rollback=Mock())
    if sqlstate == "55P03":
        with pytest.raises(HTTPException) as denied:
            locked_scalar(database, select(Conversation))
        assert denied.value.status_code == 409
        assert denied.value.headers["Retry-After"] == "1"
        database.rollback.assert_called_once_with()
    else:
        with pytest.raises(OperationalError) as raised:
            locked_scalar(database, select(Conversation))
        assert raised.value is error
        database.rollback.assert_not_called()


@pytest.mark.parametrize("suffix,payload,human", [
    ("/messages", {"content": "Concurrent AI turn"}, False),
    ("/messages", {"content": "Concurrent human inbox turn"}, True),
    ("/handoff", {"reason": "Concurrent handoff"}, False),
    ("/handoff/status", {"status": "human"}, False),
    ("/reply", {"content": "Concurrent operator reply"}, True),
])
def test_conversation_routes_reject_contended_rows_without_provider_calls(setup, monkeypatch, suffix, payload, human):
    client, factory = setup
    assert login(client).status_code == 200
    agent = client.post("/businesses/a/agents", json=AGENT).json()["id"]
    conversation = client.post(f"/businesses/a/agents/{agent}/conversations").json()["id"]
    if human:
        with factory() as database:
            database.get(Conversation, conversation).status = "human"
            database.commit()
    original_scalar = DBSession.scalar

    def contention(self, statement, *args, **kwargs):
        if getattr(statement, "_for_update_arg", None) is not None and "conversations" in str(statement):
            original = Exception("simulated contended row")
            original.sqlstate = "55P03"
            raise OperationalError("SELECT", {}, original)
        return original_scalar(self, statement, *args, **kwargs)

    async def forbidden_provider(*args):
        raise AssertionError("A contended request must never call the provider")

    monkeypatch.setattr(DBSession, "scalar", contention)
    monkeypatch.setattr("app.ai.complete", forbidden_provider)
    response = client.post(f"/businesses/a/conversations/{conversation}" + suffix, json=payload)
    assert response.status_code == 409
    assert response.headers["retry-after"] == "1"
    assert client.get("/health").status_code == 200


def test_password_work_is_bounded_across_hash_and_verify(monkeypatch):
    hasher = BoundedPasswordHasher()
    entered, release = Event(), Event()

    def slow_hash(password):
        entered.set()
        if not release.wait(5):
            raise AssertionError("Test did not release password work")
        return "test-only-password-digest"

    monkeypatch.setattr(hasher, "_hasher", SimpleNamespace(hash=slow_hash, verify=hasher._hasher.verify))
    with ThreadPoolExecutor(max_workers=1) as pool:
        work = pool.submit(hasher.hash, "test-only password")
        try:
            assert entered.wait(2)
            for operation in (lambda: hasher.hash("other password"), lambda: hasher.verify("invalid", "other password")):
                with pytest.raises(HTTPException) as denied:
                    operation()
                assert denied.value.status_code == 429
                assert denied.value.headers["Retry-After"] == "1"
        finally:
            release.set()
        assert work.result(timeout=2) == "test-only-password-digest"
    # Verification errors must release the slot too, allowing later hashing.
    from argon2.exceptions import InvalidHashError
    with pytest.raises(InvalidHashError):
        hasher.verify("invalid", "test-only password")
    assert hasher.hash("test-only password") == "test-only-password-digest"


@pytest.mark.parametrize("chunked", [False, True])
def test_oversized_body_rejected_before_password_work(setup, monkeypatch, chunked):
    client, _ = setup
    calls = []
    monkeypatch.setattr("app.main.verify", lambda *args: calls.append(args) or False)
    # Unicode payload is fewer than 64,000 characters but exceeds 64,000 bytes.
    payload = json.dumps({"email": "unknown@example.com", "password": "Wrong-password-123!", "padding": "🌱" * 17000}, ensure_ascii=False).encode()
    body = (payload[i:i + 8192] for i in range(0, len(payload), 8192)) if chunked else payload
    response = client.post("/auth/login", content=body, headers={"Content-Type": "application/json"})
    assert response.status_code == 413
    assert not calls


def test_randomized_login_targets_cannot_bypass_shared_budget(setup, monkeypatch):
    client, _ = setup
    monkeypatch.setattr(settings, "login_requests_per_minute", 10)
    hashes = []
    monkeypatch.setattr("app.main.verify", lambda password, hashed: hashes.append(hashed) or False)
    for index in range(10):
        response = client.post("/auth/login", json={"email": f"spray-{index}@example.com", "password": "Wrong-password-123!"})
        assert response.status_code == 401
    denied = client.post("/auth/login", json={"email": "new-target@example.com", "password": "Wrong-password-123!"})
    assert denied.status_code == 429
    assert int(denied.headers["retry-after"]) > 0
    assert hashes == [DUMMY_HASH] * 10


def test_row_lock_wait_does_not_freeze_health_requests(setup, monkeypatch):
    client, _ = setup
    assert login(client).status_code == 200
    agent = client.post("/businesses/a/agents", json=AGENT).json()["id"]
    conversation = client.post(f"/businesses/a/agents/{agent}/conversations").json()["id"]
    entered, release = Event(), Event()
    original_scalar = DBSession.scalar

    def blocked_scalar(self, statement, *args, **kwargs):
        # Emulate PostgreSQL waiting on a contended conversation row lock.
        # The disposable SQLite fixture cannot itself reproduce PG row locks.
        if getattr(statement, "_for_update_arg", None) is not None and "conversations" in str(statement):
            entered.set()
            if not release.wait(5):
                raise AssertionError("Test did not release the simulated row lock")
        return original_scalar(self, statement, *args, **kwargs)

    async def fake_complete(*args):
        return "Test-only reply", 3, 2

    monkeypatch.setattr(DBSession, "scalar", blocked_scalar)
    monkeypatch.setattr("app.ai.complete", fake_complete)
    with ThreadPoolExecutor(max_workers=2) as pool:
        chat = pool.submit(client.post, f"/businesses/a/conversations/{conversation}/messages", json={"content": "Hello"})
        try:
            assert entered.wait(2), "Chat did not reach the simulated row lock"
            health = pool.submit(client.get, "/health")
            assert health.result(timeout=1).status_code == 200
        finally:
            release.set()
        assert chat.result(timeout=5).status_code == 200


def test_forged_session_and_role_fields_do_not_grant_admin_access(setup):
    client, _ = setup
    client.cookies.set("session", "forged-admin-session")
    assert client.get("/auth/me").status_code == 401
    client.cookies.clear()
    response = client.post("/auth/login", json={"email": "a@example.com", "password": "Test-password-123!", "role": "admin", "business_id": "b"})
    assert response.status_code == 200
    assert response.json()["role"] == "client" and response.json()["business_id"] == "a"
    assert client.post("/businesses", json={"name": "Escalation"}).status_code == 403
    assert client.get("/businesses/b/floor").status_code == 404
    assert client.post("/businesses/a/inference/check").status_code == 403


def test_tenant_switch_cannot_read_or_mutate_foreign_conversation(setup):
    client, _ = setup
    assert login(client).status_code == 200
    agent = client.post("/businesses/b/agents", json=AGENT).json()["id"]
    conversation = client.post(f"/businesses/b/agents/{agent}/conversations").json()["id"]
    assert login(client, "a@example.com").status_code == 200
    for prefix in ("/businesses/a", "/businesses/b"):
        route = f"{prefix}/conversations/{conversation}"
        assert client.get(route + "/messages").status_code == 404
        assert client.post(route + "/messages", json={"content": "Cross-tenant write"}).status_code == 404
        assert client.post(route + "/handoff", json={"reason": "Cross-tenant handoff"}).status_code == 404

