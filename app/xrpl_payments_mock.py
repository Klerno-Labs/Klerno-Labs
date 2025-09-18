"""
XRPL Payments Module for Klerno Labs - MOCK VERSION.

This is a simplified mock version that doesn't require xrpl - py.
It provides the same interface but with mock implementations.
"""
from __future__ import annotations

import hashlib
import os
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple

# Mock class implementations


class MockJsonRpcClient:
    """Mock JSON - RPC client for XRPL."""


    def __init__(self, url: str):
        self.url=url
        print(f"Mock XRPL client initialized with URL: {url}")


    def request(self, *args, **kwargs):
        """Mock request method."""
        return {"result": {"status": "success", "validated": True}}


class MockWallet:
    """Mock XRPL wallet."""


    def __init__(self, seed: str = None, sequence: int = None):
        self.seed=seed or "mockSeedValue"
        self.sequence=sequence or 1234
        self.classic_address=f"r{hashlib.md5(str(time.time()).encode()).hexdigest()[:30]}"


    def get_xaddress(self):
        """Return a mock X - address."""
        return f"X{self.classic_address}..."

# Network selection based on settings


def get_xrpl_client() -> MockJsonRpcClient:
    """Get a mock JSON - RPC client."""
    # Simulate the network selection
    network=os.environ.get("XRPL_NET", "testnet").lower()

    if network == "mainnet":
        url="https://xrplcluster.com"
    elif network == "testnet":
        url="https://s.altnet.rippletest.net:51234"
    else:  # devnet
        url="https://s.devnet.rippletest.net:51234"

    return MockJsonRpcClient(url)


def get_network_info() -> Dict[str, Any]:
    """Get information about the currently connected XRPL network."""
    network=os.environ.get("XRPL_NET", "testnet").lower()

    return {
        "network": network,
            "explorer_url": f"https://{'testnet.' if network != 'mainnet' else ''}xrpscan.com",
            "is_test_network": network != "mainnet",
            "client_url": "https://s.altnet.rippletest.net:51234" if network == "testnet" else "https://xrplcluster.com"
    }


def create_payment_request(amount: float, destination: str = None) -> Dict[str, Any]:
    """
    Create a mock payment request.

    Args:
        amount: The amount in XRP
        destination: Optional destination address (defaults to settings)

    Returns:
        Dict with payment details
    """
    # Generate a unique payment ID
    payment_id=str(uuid.uuid4())

    # Use provided destination or fall back to settings
    dest_address=destination or os.environ.get(
        "DESTINATION_WALLET",
            "rHb9CJAWyB4rj91VRWn96DkukG4bwdtyTh",
            )

    # Create the payment request
    return {
        "payment_id": payment_id,
            "amount_xrp": amount,
            "destination": dest_address,
            "created_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(hours=24)).isoformat(),
            "status": "pending",
            "network": os.environ.get("XRPL_NET", "testnet"),
            "payment_url": f"xrpl://{dest_address}?amount={amount}&dt={payment_id}"
    }


def verify_payment(payment_id: str, tx_hash: Optional[str] = None) -> Tuple[bool, Dict[str, Any]]:
    """
    Verify a mock payment.

    Args:
        payment_id: The unique payment ID
        tx_hash: Optional transaction hash to verify

    Returns:
        Tuple of (success, details)
    """
    # In the mock version, we'll simulate a successful payment
    return (True, {
        "payment_id": payment_id,
            "tx_hash": tx_hash or f"mock_tx_hash_{hashlib.md5(payment_id.encode()).hexdigest()[:16]}",
            "verified": True,
            "verified_at": datetime.now().isoformat(),
            "ledger_index": 12345678,
            "amount_xrp": 100.0,
            "network": os.environ.get("XRPL_NET", "testnet")
    })
