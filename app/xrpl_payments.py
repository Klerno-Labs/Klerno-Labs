
from __future__ import annotations
# Dummy XRPLClient for test patching
XRPLClient=None

from datetime import timezone


def get_payment_status(payment_request: Dict[str, Any], tx_hash: Optional[str] = None) -> str:
    """Return the status of a payment request: 'verified', 'pending', or 'expired'."""
    expires_at=payment_request.get("expires_at")
    if expires_at:
        try:
            expires_dt=datetime.fromisoformat(expires_at)
            if expires_dt.tzinfo is None:
                expires_dt=expires_dt.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) > expires_dt:
                return "expired"
        except Exception:
            pass
    verified, _, _=verify_payment(payment_request, tx_hash)
    if verified:
        return "verified"
    return "pending"
"""
XRPL Payments Module for Klerno Labs.

Handles payment generation, verification, and subscription management using the XRP Ledger.
Uses xrpl - py library for XRPL interaction.
"""

import hashlib
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple

import xrpl
from xrpl.clients import JsonRpcClient
from xrpl.models.requests import AccountTx

from .config import settings


# Network selection based on settings


def get_xrpl_client() -> JsonRpcClient:
    """Get a JSON - RPC client for the XRPL network specified in settings."""
    network=settings.XRPL_NET.lower()

    if network == "mainnet":
        return JsonRpcClient("https://xrplcluster.com")
    elif network == "testnet":
        return JsonRpcClient("https://s.altnet.rippletest.net:51234")
    elif network == "devnet":
        return JsonRpcClient("https://s.devnet.rippletest.net:51234")
    else:
        # Fallback to testnet
        return JsonRpcClient("https://s.altnet.rippletest.net:51234")


def create_payment_request(
    user_id: str,
        amount_xrp: Optional[float] = None,
        description: str="Klerno Labs Subscription"
) -> Dict[str, Any]:
    """
    Create a payment request for a user.

    Args:
        user_id: User ID
        amount_xrp: Amount in XRP (if None, use settings.SUB_PRICE_XRP)
        description: Payment description

    Returns:
        Dict containing payment details
    """
    payment_id=str(uuid.uuid4())
    amount=amount_xrp if amount_xrp is not None else settings.SUB_PRICE_XRP

    # Create a unique identifier for this payment (used in memo field)
    payment_code=hashlib.sha256(f"{payment_id}:{user_id}:{time.time()}".encode()).hexdigest()[:16]

    payment_request={
        "id": payment_id,
            "user_id": user_id,
            "destination": settings.DESTINATION_WALLET,
            "amount_xrp": amount,
            "description": description,
            "payment_code": payment_code,
            "network": settings.XRPL_NET,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat(),
            "status": "pending"
    }

    return payment_request


def verify_payment(
    payment_request: Dict[str, Any],
        tx_hash: Optional[str] = None
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    # Check for expiration before verifying payment
    expires_at=payment_request.get("expires_at")
    if expires_at:
        try:
            expires_dt=datetime.fromisoformat(expires_at)
            if expires_dt.tzinfo is None:
                expires_dt=expires_dt.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) > expires_dt:
                return False, "Payment request expired", None
        except Exception:
            pass
    """
    Verify if a payment has been made according to the request.

    This function checks the XRPL for a payment matching the request details.

    Args:
        payment_request: Payment request dictionary
        tx_hash: Transaction hash (optional, speeds up verification)

    Returns:
        Tuple of (is_verified, message, transaction_details)
    """
    try:
        client=get_xrpl_client()
        destination=payment_request["destination"]
        payment_code=payment_request["payment_code"]
        amount_xrp=payment_request["amount_xrp"]

        # If we have a transaction hash, verify that specific transaction
        if tx_hash:
            tx_response=client.request(xrpl.models.requests.Tx(transaction=tx_hash))
            if not tx_response.is_successful():
                return False, f"Failed to fetch transaction: {tx_response.result}", None

            tx_result=tx_response.result
            tx=(
                tx_result.get("Transactions", [])[0]
                if isinstance(tx_result.get("Transactions"), list)
                else tx_result
            )

            # Verify it's a payment
            if tx.get("TransactionType") != "Payment":
                return False, "Transaction is not a Payment", None

            # Verify amount
            drops=tx.get("Amount", "0")
            if isinstance(drops, dict):  # This would be a non - XRP currency
                return False, "Payment is not in XRP", None

            tx_amount_xrp=float(drops) / 1_000_000.0  # Convert drops to XRP

            if tx_amount_xrp < amount_xrp:
                return (
                    False,
                        f"Payment amount too low: {tx_amount_xrp} XRP < {amount_xrp} XRP",
                        None,
                        )

            # Verify destination
            if tx.get("Destination", "").lower() != destination.lower():
                return False, "Payment was sent to a different destination", None

            # Verify memo if it exists
            memos=tx.get("Memos", [])
            memo_found=False
            for memo in memos:
                memo_data=memo.get("Memo", {}).get("MemoData", "")
                if payment_code in memo_data:
                    memo_found=True
                    break

            if not memo_found:
                # We'll accept payments without the memo, but it's not ideal
                pass

            # Transaction is verified
            tx_details={
                "tx_hash": tx_hash,
                    "amount_xrp": tx_amount_xrp,
                    "from_account": tx.get("Account", ""),
                    "to_account": tx.get("Destination", ""),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "memo_verified": memo_found
            }

            return True, "Payment verified", tx_details

        else:
            # Without a hash, we need to search recent transactions to the destination
            request=AccountTx(account=destination, limit=20)
            response=client.request(request)

            if not response.is_successful():
                return False, f"Failed to fetch account transactions: {response.result}", None

            transactions=response.result.get("transactions", [])

            for tx_info in transactions:
                tx=tx_info.get("tx", {})

                # Skip non - payments
                if tx.get("TransactionType") != "Payment":
                    continue

                # Verify amount
                drops=tx.get("Amount", "0")
                if isinstance(drops, dict):  # This would be a non - XRP currency
                    continue

                tx_amount_xrp=float(drops) / 1_000_000.0  # Convert drops to XRP

                if tx_amount_xrp < amount_xrp * 0.99:  # Allow for 1% variation
                    continue

                # Verify destination
                if tx.get("Destination", "").lower() != destination.lower():
                    continue

                # Check if the transaction has the memo
                memos=tx.get("Memos", [])
                memo_found=False
                for memo in memos:
                    memo_data=memo.get("Memo", {}).get("MemoData", "")
                    if payment_code in memo_data:
                        memo_found=True
                        break

                # If memo is found, this is our payment
                if memo_found:
                    tx_details={
                        "tx_hash": tx.get("hash", ""),
                            "amount_xrp": tx_amount_xrp,
                            "from_account": tx.get("Account", ""),
                            "to_account": tx.get("Destination", ""),
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "memo_verified": True
                    }
                    return True, "Payment verified with memo", tx_details

            # If we're here, we didn't find a matching payment
            return False, "No matching payment found", None

    except Exception as e:
        return False, f"Error verifying payment: {str(e)}", None


def get_network_info() -> Dict[str, Any]:
    """Get information about the current XRPL network."""
    client=get_xrpl_client()

    try:
        server_info=client.request(xrpl.models.requests.ServerInfo())
        if server_info.is_successful():
            info=server_info.result
            return {
                "network": settings.XRPL_NET,
                    "connected": True,
                    "server_state": info.get("info", {}).get("server_state", "unknown"),
                    "validated_ledger": info.get("info", {}).get("validated_ledger", {}),
                    "destination_wallet": settings.DESTINATION_WALLET,
                    "subscription_price_xrp": settings.SUB_PRICE_XRP,
                    "subscription_duration_days": settings.SUB_DURATION_DAYS
            }
    except Exception:
        pass

    return {
        "network": settings.XRPL_NET,
            "connected": False,
            "destination_wallet": settings.DESTINATION_WALLET,
            "subscription_price_xrp": settings.SUB_PRICE_XRP,
            "subscription_duration_days": settings.SUB_DURATION_DAYS
    }


def create_xumm_payload(payment_request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a payload for XUMM wallet integration.

    This is a simplified version without actual XUMM API integration.
    In a production environment, you'd use the XUMM API to create a payload.

    Returns a dictionary with the payment details and a QR code URL (mocked).
    """
    return {
        "payment_request": payment_request,
            "xrpl_network": settings.XRPL_NET,
            "xumm_url": f"https://xumm.app / sign/{payment_request['id']}",
            "qr_code_url": f"https://api.qrserver.com / v1 / create - qr - code/?size=300x300&data={settings.DESTINATION_WALLET}:{payment_request['amount_xrp']}",
            "deeplink": f"xumm://xumm.app / sign/{payment_request['id']}"
    }
