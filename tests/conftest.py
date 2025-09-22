import contextlib
import os
import sys
from pathlib import Path

# Ensure the workspace root (two levels up from this tests folder) is on sys.path
# so tests that import `app` (which lives at the workspace root) can find it.
ROOT = str(Path(__file__).resolve().parents[2])
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Legacy builtins injection removed: tests should import token helpers
# explicitly from `app.auth` or `app.security_session`.

import asyncio
import sqlite3
import tempfile
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

# Optional: expose a simple fixture for tests that need the app path

try:
    import pytest_asyncio
except Exception:
    pytest_asyncio = None


@pytest.fixture(scope="session")
def workspace_root():
    return ROOT



@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_db():
    """Create a temporary test database."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        db_path = tmp_file.name

    # Initialize test database
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            hashed_password TEXT NOT NULL,
            is_active BOOLEAN DEFAULT 1,
            is_admin BOOLEAN DEFAULT 0,
            subscription_status TEXT DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    )
    conn.execute(
        """
        CREATE TABLE transactions (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            amount DECIMAL(10, 2) NOT NULL,
            currency TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """
    )
    conn.execute(
        """
        CREATE TABLE compliance_tags (
            id INTEGER PRIMARY KEY,
            transaction_id INTEGER NOT NULL,
            tag_type TEXT NOT NULL,
            confidence REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (transaction_id) REFERENCES transactions (id)
        )
    """
    )
    conn.commit()
    conn.close()

    yield db_path

    # Cleanup: close any lingering connections by forcing GC and retry unlink on Windows
    import gc
    import time

    gc.collect()
    for _ in range(5):
        try:
            Path(db_path).unlink()
            break
        except PermissionError:
            # File may be locked on Windows; wait and retry
            time.sleep(0.2)
    else:
        # Last attempt: try removing via Path.unlink and ignore errors
        try:
            Path(db_path).unlink(missing_ok=True)
        except Exception:
            pass


@pytest.fixture
def test_client(test_db):
    """Create a test client with temporary database."""
    os.environ["DATABASE_URL"] = f"sqlite:///{test_db}"

    from app.main import app

    with TestClient(app) as client:
        yield client


if pytest_asyncio:
    @pytest_asyncio.fixture
    async def async_client(test_db):
        """Create an async test client (pytest-asyncio mode)."""
        os.environ["DATABASE_URL"] = f"sqlite:///{test_db}"

        from app.main import app

        # Use ASGITransport for compatibility with newer httpx versions
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client
else:
    @pytest.fixture
    async def async_client(test_db):
        """Fallback async client fixture when pytest-asyncio not installed."""
        os.environ["DATABASE_URL"] = f"sqlite:///{test_db}"

        from app.main import app

        # Use ASGITransport for compatibility with newer httpx versions
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client


@pytest.fixture
def mock_user():
    """Create a mock user for testing."""
    return {
        "id": 1,
        "email": "test@example.com",
        "hashed_password": "$2b$12$test_hash",
        "is_active": True,
        "is_admin": False,
    }


@pytest.fixture
def mock_admin_user():
    """Create a mock admin user for testing."""
    return {
        "id": 2,
        "email": "admin@example.com",
        "hashed_password": "$2b$12$admin_hash",
        "is_active": True,
        "is_admin": True,
    }


@pytest.fixture
def mock_transaction():
    """Create a mock transaction for testing."""
    return {
        "id": 1,
        "user_id": 1,
        "amount": 100.50,
        "currency": "USD",
        "status": "completed",
        "created_at": datetime.utcnow(),
    }


@pytest.fixture
def mock_xrpl_client():
    """Create a mock XRPL client for testing."""
    mock_client = Mock()
    mock_client.is_connected.return_value = True
    mock_client.get_account_info = AsyncMock(
        return_value={"account_data": {"Account": "rTest123", "Balance": "1000000000"}}
    )
    return mock_client


@pytest.fixture
def sample_iso20022_message():
    """Create a sample ISO 20022 message for testing."""
    return """<?xml version="1.0" encoding="UTF-8"?>
    <Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.02">
        <FIToFICstmrCdtTrf>
            <GrpHdr>
                <MsgId>MSG123456</MsgId>
                <CreDtTm>2023-10-01T10:00:00Z</CreDtTm>
                <NbOfTxs>1</NbOfTxs>
                <SttlmInf>
                    <SttlmMtd>CLRG</SttlmMtd>
                </SttlmInf>
            </GrpHdr>
            <CdtTrfTxInf>
                <PmtId>
                    <InstrId>INSTR123</InstrId>
                    <EndToEndId>E2E123</EndToEndId>
                </PmtId>
                <IntrBkSttlmAmt Ccy="USD">1000.00</IntrBkSttlmAmt>
                <Dbtr>
                    <Nm>Test Debtor</Nm>
                </Dbtr>
                <Cdtr>
                    <Nm>Test Creditor</Nm>
                </Cdtr>
            </CdtTrfTxInf>
        </FIToFICstmrCdtTrf>
    </Document>"""


class DatabaseTestUtils:
    """Utilities for database testing."""

    @staticmethod
    def create_test_user(db_path: str, user_data: dict[str, Any]) -> int:
        """Create a test user in the database."""
        conn = sqlite3.connect(db_path, timeout=5.0)
        cursor = conn.cursor()

        # Try to insert; if the email already exists, return existing id.
        cursor.execute(
            "INSERT OR IGNORE INTO users (email, hashed_password, is_active, is_admin) VALUES (?, ?, ?, ?)",
            (
                user_data["email"],
                user_data["hashed_password"],
                user_data["is_active"],
                user_data["is_admin"],
            ),
        )
        conn.commit()

        # Fetch id (either newly inserted or existing)
        cursor.execute("SELECT id FROM users WHERE email = ?", (user_data["email"],))
        row = cursor.fetchone()
        user_id = row[0] if row else 0
        # If the test provided a subscription_status, update the row so paid tests
        # can mark users as having an active subscription across the session.
        if "subscription_status" in user_data:
            try:
                cursor.execute(
                    "UPDATE users SET subscription_status = ? WHERE email = ?",
                    (user_data.get("subscription_status"), user_data["email"]),
                )
                conn.commit()
            except Exception:
                # Best-effort update; ignore if the column doesn't exist
                pass
        conn.close()
        return user_id

    @staticmethod
    def create_test_transaction(db_path: str, transaction_data: dict[str, Any]) -> int:
        """Create a test transaction in the database."""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO transactions (user_id, amount, currency, status) VALUES (?, ?, ?, ?)",
            (
                transaction_data["user_id"],
                transaction_data["amount"],
                transaction_data["currency"],
                transaction_data["status"],
            ),
        )
        transaction_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return transaction_id


class APITestUtils:
    """Utilities for API testing."""

    @staticmethod
    def authenticate_user(client: TestClient, email: str, password: str) -> str:
        """Authenticate user and return access token."""
        response = client.post(
            "/auth/login", data={"username": email, "password": password}
        )
        assert response.status_code == 200
        return response.json()["access_token"]

    @staticmethod
    def get_auth_headers(token: str) -> dict[str, str]:
        """Get authorization headers for API requests."""
        return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def db_utils():
    """Database test utilities fixture."""
    return DatabaseTestUtils()


@pytest.fixture
def api_utils():
    """API test utilities fixture."""
    return APITestUtils()
