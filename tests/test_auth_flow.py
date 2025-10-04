import importlib
import os
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient


def test_login_api_with_temp_sqlite_db():
    # Create a temp DB file
    tmp = tempfile.NamedTemporaryFile(
        prefix="klerno_test_pytest_", suffix=".db", delete=False,
    )
    db_path = tmp.name
    tmp.close()

    # Ensure env is set before importing app modules
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ["DB_PATH"] = db_path

    # Import app and reload key modules so they pick up the env
    import app.main as main_mod

    importlib.reload(main_mod)

    # Reload store and security_session to ensure they use the new DATABASE_URL
    from app import store

    importlib.reload(store)

    import app.security_session as sec

    importlib.reload(sec)

    # Initialize DB schema for this temp DB
    store.init_db()

    # Create a user using the canonical create_user helper and the app's hasher
    password = "testpassword"
    pw_hash = sec.hash_pw(password)
    user = store.create_user(
        email="pytest_test@example.com",
        password_hash=pw_hash,
        role="viewer",
        subscription_active=True,
    )
    assert user is not None

    # Create TestClient and call the API
    client = TestClient(main_mod.app)

    resp = client.post(
        "/auth/login/api",
        json={"email": "pytest_test@example.com", "password": password},
    )
    assert (
        resp.status_code == 200
    ), f"unexpected status: {resp.status_code} body={resp.text}"
    j = resp.json()
    assert j.get("ok") is True
    assert j.get("user", {}).get("email") == "pytest_test@example.com"

    # Cleanup
    try:
        Path(db_path).unlink()
    except Exception:
        pass
