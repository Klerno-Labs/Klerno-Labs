"""
Common pytest fixtures and test configuration.
"""
import os
import pytest
from datetime import datetime

# Set test environment
os.environ["APP_ENV"] = "test"
os.environ["XRPL_NET"] = "testnet"
os.environ["DESTINATION_WALLET"] = "rPT1Sjq2YGrBMTttX4GZHjKu9dyfzbpAYe"
os.environ["SUB_PRICE_XRP"] = "10"
os.environ["SUB_DURATION_DAYS"] = "30"


@pytest.fixture
def test_user():
    """Fixture to provide a test user."""
    return {
        "id": "test_user_id",
        "email": "test@example.com",
        "username": "testuser",
    }


@pytest.fixture
def mock_datetime(monkeypatch):
    """Fixture to mock datetime for consistent testing."""
    class MockDateTime:
        @classmethod
        def now(cls):
            return datetime(2025, 9, 14, 12, 0, 0)
    
    monkeypatch.setattr('app.xrpl_payments.datetime', MockDateTime)
    monkeypatch.setattr('app.subscriptions.datetime', MockDateTime)
    return MockDateTime