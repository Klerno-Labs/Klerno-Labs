# Mock implementation of XRPL functionality
import random
from datetime import datetime


class XRPLError(Exception):
    """Base exception for XRPL errors"""

    pass


def create_payment_request(amount, recipient, sender=None, memo=None):
    """Create a mock payment request"""
    request_id = f"req_{random.randint(100000, 999999)}"
    return {
        "request_id": request_id,
        "amount": amount,
        "recipient": recipient,
        "sender": sender,
        "memo": memo,
        "timestamp": str(datetime.now()),
        "expiration": str(datetime.now().timestamp() + 3600),
        "status": "pending",
        "network": "testnet",
        "mock": True,
    }


def verify_payment(request_id):
    """Verify a mock payment"""
    # Always return success for mock payments
    return {
        "request_id": request_id,
        "verified": True,
        "amount_received": random.uniform(0.1, 100.0),
        "timestamp": str(datetime.now()),
        "transaction_hash": f"mock_tx_{random.randint(100000, 999999)}",
        "mock": True,
    }


def get_network_info():
    """Get mock network info"""
    return {
        "network": "testnet",
        "status": "online",
        "fee": random.uniform(0.00001, 0.0001),
        "last_ledger": random.randint(10000000, 99999999),
        "validators_online": random.randint(20, 30),
        "mock": True,
    }
