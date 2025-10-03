import os
import tempfile
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_login_form_returns_json_and_cookie_isolated_db():
    """Exercise the form-based /auth/login endpoint with an isolated DB.

    Flow: register (JSON) -> login (form) and assert JSON ok + session cookie set.
    """
    # Setup isolated sqlite DB for this test
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = Path(tmp.name)

    prev_db = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path.as_posix()}"

    # Initialize schema
    from app import store

    store.init_db()

    from app.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # 1) Register a user
        email = "formlogin@example.com"
        password = "Str0ng!Passw0rd"
        r = await client.post(
            "/auth/register", json={"email": email, "password": password}
        )
        assert r.status_code in (200, 201)

        # 2) Login using form-encoded data
        r = await client.post(
            "/auth/login",
            data={"email": email, "password": password},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data.get("ok") is True
        assert "access_token" in data
        # Cookie should be set for session management
        cookie_hdr = r.headers.get("set-cookie")
        assert cookie_hdr and "session=" in cookie_hdr

    # Cleanup env
    if prev_db is not None:
        os.environ["DATABASE_URL"] = prev_db
    else:
        os.environ.pop("DATABASE_URL", None)
    try:
        db_path.unlink(missing_ok=True)
    except Exception:
        pass
