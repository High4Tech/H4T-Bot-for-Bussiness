import hashlib
import hmac
import json
import secrets
import pytest
from fastapi.testclient import TestClient
from server.app import create_app, password_hash, COOKIE

ORIGIN = {"Origin": "http://127.0.0.1:5173"}
PASSWORD = "Synthetic-Test-Passphrase-2026"

def owner(app, email="owner@example.test", company="Example Business"):
    client = TestClient(app)
    response = client.post("/api/auth/register", json=dict(email=email, password=PASSWORD, name="Sample Owner", company=company), headers=ORIGIN)
    assert response.status_code == 201
    return client, response.json(), response

def test_session_hash_cookie_and_logout(service):
    client, user, response = owner(service)
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=strict" in cookie and "path=/api" in cookie
    token = client.cookies.get(COOKIE)
    with service.state.db() as db:
        stored = db.execute("SELECT password_hash FROM users").fetchone()["password_hash"]
        session = db.execute("SELECT hash FROM sessions").fetchone()["hash"]
    assert PASSWORD not in stored and stored.startswith("scrypt:")
    assert session == hashlib.sha256(token.encode()).hexdigest()
    assert client.get("/api/auth/me").json()["id"] == user["id"]
    assert "password_hash" not in client.get("/api/auth/me").text
    assert client.post("/api/auth/logout", headers=ORIGIN).status_code == 204
    client.cookies.set(COOKIE, token, path="/api")
    assert client.get("/api/auth/me").status_code == 401

def test_signin_and_origin_rejection(service):
    client, user, _ = owner(service)
    client.cookies.clear()
    assert client.post("/api/auth/login", json=dict(email=user["email"], password=PASSWORD)).status_code == 403
    assert client.post("/api/auth/login", json=dict(email=user["email"], password="Wrong-Password-Value"), headers=ORIGIN).status_code == 401
    assert client.post("/api/auth/login", json=dict(email=user["email"], password=PASSWORD), headers=ORIGIN).status_code == 200
    assert client.get("/api/company").status_code == 200
    assert TestClient(service).get("/api/company").status_code == 401

def test_workspace_isolation_and_public_appearance(service):
    a, ua, _ = owner(service, "a@example.test", "Company A")
    b, ub, _ = owner(service, "b@example.test", "Company B")
    config = a.get("/api/company").json()["appearance"]
    config["welcome"] = "Only Company A saves this welcome"
    config["id"] = ub["botId"]  # Cannot reassign ownership through body data.
    saved = a.put("/api/company/appearance", json=config, headers=ORIGIN)
    assert saved.status_code == 200 and saved.json()["id"] == ua["botId"]
    assert b.get("/api/company").json()["appearance"]["welcome"] != config["welcome"]
    public = TestClient(service).get("/api/embed/" + ua["botId"]).json()
    assert set(public) == {"appearance", "mode"}
    assert "email" not in public["appearance"] and "companyId" not in public["appearance"]
    assert a.get("/api/platform/companies").status_code == 403
    config["avatar"] = "https://tracker.example/avatar.png"
    assert a.put("/api/company/appearance", json=config, headers=ORIGIN).status_code == 422

def test_operator_metadata_boundary(service):
    owner(service)
    with service.state.db() as db:
        db.execute("INSERT INTO users VALUES(?,?,?,?,?,?)", (secrets.token_hex(16), "operator@example.test", "Operator", password_hash(PASSWORD), None, "platform_admin"))
    operator = TestClient(service)
    assert operator.post("/api/auth/login", json=dict(email="operator@example.test", password=PASSWORD), headers=ORIGIN).status_code == 200
    result = operator.get("/api/platform/companies")
    assert result.status_code == 200
    assert set(result.json()[0]) == {"id", "name", "botId", "bots", "plan", "status", "answers"}
    for endpoint in ("/api/company", "/api/company/channels", "/api/company/channel-events"):
        assert operator.get(endpoint).status_code == 403

def signed(client, payload, secret="test-meta-secret", channel="whatsapp"):
    body = json.dumps(payload).encode()
    signature = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return client.post("/api/webhooks/" + channel, content=body, headers={"X-Hub-Signature-256": signature, "Content-Type": "application/json"})

def test_meta_signature_routing_idempotency_and_conflicts(service, monkeypatch):
    monkeypatch.setenv("H4T_META_APP_SECRET", "test-meta-secret")
    monkeypatch.setenv("H4T_META_VERIFY_TOKEN", "test-verify")
    a, _, _ = owner(service, "a@example.test")
    b, _, _ = owner(service, "b@example.test")
    setup = dict(enabled=True, provider_id="phone_123")
    assert a.put("/api/company/channels/whatsapp", json=setup, headers=ORIGIN).status_code == 200
    assert b.put("/api/company/channels/whatsapp", json=setup, headers=ORIGIN).status_code == 409
    client = TestClient(service)
    q = {"hub.mode": "subscribe", "hub.verify_token": "test-verify", "hub.challenge": "sample-challenge"}
    assert client.get("/api/webhooks/whatsapp", params=q).text == "sample-challenge"
    payload = {"entry": [{"changes": [{"value": {"metadata": {"phone_number_id": "phone_123"}, "messages": [{"id": "sample-message-1", "text": {"body": "Synthetic private content"}}]}}]}]}
    assert signed(client, payload, "wrong-secret").status_code == 403
    assert signed(client, payload).json()["accepted"] == 1
    assert signed(client, payload).json()["accepted"] == 0
    assert len(a.get("/api/company/channel-events").json()) == 1
    assert b.get("/api/company/channel-events").json() == []
    assert "Synthetic private content" not in a.get("/api/company/channel-events").text
    assert signed(client, {"entry": [{"changes": {"bad": "type"}}, {"changes": [{"value": {"metadata": []}}]}]}).status_code == 200
    assert a.put("/api/company/channels/facebook", json=dict(enabled=True, provider_id="page_123"), headers=ORIGIN).status_code == 200
    assert signed(client, {"entry": [{"id": "page_123", "messaging": [{"message": {"mid": "test-mid"}}]}]}, channel="facebook").json()["accepted"] == 1

def test_auth_rate_limit_and_body_limit(service):
    client = TestClient(service)
    for _ in range(10):
        assert client.post("/api/auth/login", json=dict(email="absent@example.test", password=PASSWORD), headers=ORIGIN).status_code == 401
    assert client.post("/api/auth/login", json=dict(email="absent@example.test", password=PASSWORD), headers=ORIGIN).status_code == 429
    assert client.post("/api/auth/login", content=b"x" * 1600001, headers=ORIGIN).status_code == 413
    assert client.get("/api/health", headers={"Host": "foreign.example"}).status_code == 400
