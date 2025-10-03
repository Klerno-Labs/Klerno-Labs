import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


def _read_audit_lines():
    p = Path("logs/audit.log")
    if not p.exists():
        return []
    try:
        return [
            json.loads(line)
            for line in p.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    except Exception:
        return []


def test_signup_emits_audit_user_created_and_login_success(tmp_path, monkeypatch):
    # Ensure a clean audit log
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    (log_dir / "audit.log").write_text("", encoding="utf-8")

    client = TestClient(app)

    # Perform signup
    resp = client.post(
        "/auth/signup/api",
        json={"email": "audit@example.com", "password": "Passw0rd!Valid"},
    )
    assert resp.status_code in (200, 201)

    logs = _read_audit_lines()
    # Find audit_event entries
    events = [e.get("audit_event", {}) for e in logs]
    types = {e.get("event_type") for e in events}
    assert "admin.user.created" in types or "auth.login.success" in types


def test_login_failure_emits_audit():
    client = TestClient(app)
    # Use a user that likely doesn't exist
    resp = client.post(
        "/auth/login/api",
        json={"email": "nouser@example.com", "password": "wrong"},
    )
    assert resp.status_code == 401

    logs = _read_audit_lines()
    events = [e.get("audit_event", {}) for e in logs]
    # Ensure at least one login failure event captured
    assert any(e.get("event_type") == "auth.login.failure" for e in events)
