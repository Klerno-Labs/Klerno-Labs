import importlib
import os
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient


def setup_temp_db():
    tmp = tempfile.NamedTemporaryFile(
        prefix="klerno_test_pytest_",
        suffix=".db",
        delete=False,
    )
    db_path = tmp.name
    tmp.close()
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ["DB_PATH"] = db_path
    return db_path


def teardown_db(path) -> None:
    try:
        Path(path).unlink()
    except Exception:
        pass


def test_form_login_and_cookie() -> None:
    db_path = setup_temp_db()

    import app.main as main_mod

    importlib.reload(main_mod)
    from app import store

    importlib.reload(store)
    import app.security_session as sec

    importlib.reload(sec)

    store.init_db()

    pw = "formpw"
    ph = sec.hash_pw(pw)
    store.create_user(
        email="form_user@example.com",
        password_hash=ph,
        role="viewer",
        subscription_active=True,
    )

    client = TestClient(main_mod.app)

    # Simulate form login which sets a session cookie
    resp = client.post(
        "/auth/login",
        data={"email": "form_user@example.com", "password": pw},
    )
    assert resp.status_code == 200
    # Ensure cookie set
    cookies = resp.cookies
    assert "session" in cookies
    # Ensure the TestClient will send the session cookie on subsequent requests
    client.cookies.set("session", cookies.get("session"))

    # Now access a protected endpoint that requires a user via session
    # Use /auth/mfa/setup which requires authentication
    resp2 = client.get("/auth/mfa/setup")
    # Should be 200 if user is authenticated and no MFA configured (or 400 if missing secret)
    assert resp2.status_code in (200, 400)

    teardown_db(db_path)
