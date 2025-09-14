"""
Unit tests for data models and validation.
"""
import pytest
from decimal import Decimal
from datetime import datetime
from pydantic import ValidationError

from app.models import Transaction, TaggedTransaction, ReportRequest, ReportSummary


class TestTransaction:
    """Test Transaction model validation."""

    def test_valid_transaction(self):
        """Test creating a valid transaction."""
        tx = Transaction(
            tx_id="test_123",
            timestamp=datetime.now(),
            chain="XRP",
            from_addr="rTestFrom",
            to_addr="rTestTo",
            amount=Decimal("100.5"),
            memo="test memo",
            fee=Decimal("0.1")
        )
        assert tx.tx_id == "test_123"
        assert tx.chain == "XRP"
        assert tx.amount == Decimal("100.5")

    def test_transaction_defaults(self):
        """Test transaction with default values."""
        tx = Transaction()
        assert tx.tx_id == ""
        assert tx.chain == "XRP"
        assert tx.amount == Decimal("0")
        assert tx.direction == "out"

    def test_transaction_negative_amount(self):
        """Test transaction with negative amount."""
        # This should be allowed as outgoing transactions can be negative
        tx = Transaction(
            tx_id="test_123",
            from_addr="rTestFrom",
            to_addr="rTestTo",
            amount=Decimal("-100.5"),
            memo="test memo",
            fee=Decimal("0.1")
        )
        assert tx.amount == Decimal("-100.5")

    def test_transaction_zero_fee(self):
        """Test transaction with zero fee."""
        tx = Transaction(
            tx_id="test_123",
            from_addr="rTestFrom",
            to_addr="rTestTo",
            amount=Decimal("100.5"),
            memo="test memo",
            fee=Decimal("0")
        )
        assert tx.fee == Decimal("0")

    def test_transaction_address_properties(self):
        """Test address property aliases."""
        tx = Transaction(
            from_addr="rTestFrom",
            to_addr="rTestTo"
        )
        assert tx.from_address == "rTestFrom"
        assert tx.to_address == "rTestTo"


class TestTaggedTransaction:
    """Test TaggedTransaction model validation."""

    def test_valid_tagged_transaction(self):
        """Test creating a valid tagged transaction."""
        tx = TaggedTransaction(
            tx_id="test_123",
            timestamp=datetime.now(),
            chain="XRP",
            from_addr="rTestFrom",
            to_addr="rTestTo",
            amount=Decimal("100.5"),
            direction="out",
            memo="test memo",
            fee=Decimal("0.1"),
            risk_score=0.75,
            category="transfer"
        )
        assert tx.risk_score == 0.75
        assert tx.category == "transfer"

    def test_risk_score_bounds(self):
        """Test risk score validation bounds."""
        # Valid risk score
        tx = TaggedTransaction(
            tx_id="test_123",
            timestamp=datetime.now(),
            chain="XRP",
            from_addr="rTestFrom",
            to_addr="rTestTo",
            amount=Decimal("100.5"),
            direction="out",
            memo="test memo",
            fee=Decimal("0.1"),
            risk_score=0.5,
            category="transfer"
        )
        assert tx.risk_score == 0.5

        # Risk score at boundaries should be valid
        tx_low = TaggedTransaction(
            tx_id="test_124",
            timestamp=datetime.now(),
            chain="XRP",
            from_addr="rTestFrom",
            to_addr="rTestTo",
            amount=Decimal("100.5"),
            direction="out",
            memo="test memo",
            fee=Decimal("0.1"),
            risk_score=0.0,
            category="transfer"
        )
        assert tx_low.risk_score == 0.0

        tx_high = TaggedTransaction(
            tx_id="test_125",
            timestamp=datetime.now(),
            chain="XRP",
            from_addr="rTestFrom",
            to_addr="rTestTo",
            amount=Decimal("100.5"),
            direction="out",
            memo="test memo",
            fee=Decimal("0.1"),
            risk_score=1.0,
            category="transfer"
        )
        assert tx_high.risk_score == 1.0

    def test_address_aliases(self):
        """Test address field aliases."""
        tx = TaggedTransaction(
            tx_id="test_123",
            timestamp=datetime.now(),
            chain="XRP",
            from_address="rTestFrom",  # Using alias
            to_address="rTestTo",     # Using alias
            amount=Decimal("100.5"),
            direction="out",
            category="transfer"
        )
        assert tx.from_addr == "rTestFrom"
        assert tx.to_addr == "rTestTo"
        assert tx.from_address == "rTestFrom"
        assert tx.to_address == "rTestTo"


class TestReportRequest:
    """Test ReportRequest model validation."""

    def test_valid_report_request(self):
        """Test creating a valid report request."""
        request = ReportRequest(
            address="rTestWallet",
            start=datetime(2024, 1, 1),
            end=datetime(2024, 12, 31),
            chain="XRP"
        )
        assert request.address == "rTestWallet"
        assert request.chain == "XRP"

    def test_report_request_defaults(self):
        """Test report request with default values."""
        request = ReportRequest()
        assert request.chain == "XRP"
        assert len(request.wallet_addresses) == 0

    def test_report_request_with_wallets(self):
        """Test report request with wallet addresses."""
        request = ReportRequest(
            wallet_addresses=["rWallet1", "rWallet2"]
        )
        assert len(request.wallet_addresses) == 2
        assert "rWallet1" in request.wallet_addresses


class TestReportSummary:
    """Test ReportSummary model validation."""

    def test_valid_report_summary(self):
        """Test creating a valid report summary."""
        summary = ReportSummary(
            total_transactions=100,
            total_volume=Decimal("10000.50"),
            high_risk_count=5,
            categories={"transfer": 80, "fee": 15, "exchange": 5}
        )
        assert summary.total_transactions == 100
        assert summary.total_volume == Decimal("10000.50")
        assert summary.high_risk_count == 5
        assert len(summary.categories) == 3

    def test_report_summary_empty_categories(self):
        """Test report summary with empty categories."""
        summary = ReportSummary(
            total_transactions=0,
            total_volume=Decimal("0"),
            high_risk_count=0,
            categories={}
        )
        assert summary.total_transactions == 0
        assert len(summary.categories) == 0


class TestModelSerialization:
    """Test model serialization and deserialization."""

    def test_transaction_json_serialization(self):
        """Test TaggedTransaction JSON serialization."""
        tx = TaggedTransaction(
            tx_id="test_123",
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            chain="XRP",
            from_addr="rTestFrom",
            to_addr="rTestTo",
            amount=Decimal("100.5"),
            direction="out",
            memo="test memo",
            fee=Decimal("0.1")
        )
        
        # Test conversion to dict
        tx_dict = tx.model_dump()
        assert tx_dict["tx_id"] == "test_123"
        assert tx_dict["chain"] == "XRP"
        
        # Test JSON serialization
        tx_json = tx.model_dump_json()
        assert isinstance(tx_json, str)
        assert "test_123" in tx_json

    def test_transaction_json_deserialization(self):
        """Test TaggedTransaction JSON deserialization."""
        tx_data = {
            "tx_id": "test_123",
            "timestamp": "2024-01-01T12:00:00",
            "chain": "XRP",
            "from_addr": "rTestFrom",
            "to_addr": "rTestTo",
            "amount": "100.5",
            "direction": "out",
            "memo": "test memo",
            "fee": "0.1"
        }
        
        tx = TaggedTransaction(**tx_data)
        assert tx.tx_id == "test_123"
        assert tx.amount == Decimal("100.5")
        assert tx.fee == Decimal("0.1")