from __future__ import annotations

import os
from datetime import datetime
from typing import TYPE_CHECKING, Any

import requests

if TYPE_CHECKING:
    # Avoid requiring app.models to be importable at type-check time
    Transaction: Any

# Transaction model is imported inside the function to avoid top-level import issues


def xrpl_json_to_transactions(account: str, tx_list: list[dict]):
    # Import Transaction dynamically to avoid import-time package-layout issues
    try:
        import importlib

        mod = importlib.import_module("app.models")
    except Exception:
        import importlib

        mod = importlib.import_module("..models", package=__package__)

    Transaction = getattr(mod, "Transaction")

    out = []
    for item in tx_list:
        tx = item.get("tx", {})
        tx_id = tx.get("hash", "unknown")
        timestamp = datetime.utcfromtimestamp(
            tx.get("date", 0) + 946684800
        )  # XRPL epoch → UNIX
        from_addr = tx.get("Account", account)
        to_addr = tx.get("Destination", account)
        amount_drops = tx.get("Amount", "0")
        try:
            amount = float(amount_drops) / 1_000_000.0
        except Exception:
            amount = 0.0
        direction = "out" if from_addr == account else "in"
        fee = float(tx.get("Fee", "0")) / 1_000_000.0
        out.append(
            Transaction(
                tx_id=tx_id,
                timestamp=timestamp,
                chain="XRP",
                from_addr=from_addr,
                to_addr=to_addr,
                amount=amount,
                symbol="XRP",
                direction=direction,
                memo=None,
                fee=fee,
            )
        )
    return out


# --- Read - only XRPL fetch (public endpoint) ---


def fetch_account_tx(account: str, limit: int = 10) -> list[dict]:
    """
    Uses XRPL JSON - RPC 'account_tx' to fetch recent transactions for an account.
    Read - only. No keys. Safe to try.
    """
    url = os.getenv(
        "XRPL_RPC_URL", "https://s1.ripple.com:51234"
    )  # public Ripple server
    payload = {
        "method": "account_tx",
        "params": [
            {
                "account": account,
                "ledger_index_min": -1,
                "ledger_index_max": -1,
                "limit": int(limit),
            }
        ],
    }
    try:
        r = requests.post(url, json=payload, timeout=15)
        r.raise_for_status()
        data = r.json()
        # XRPL returns {"result": {"transactions": [...]}}
        return data.get("result", {}).get("transactions", [])
    except Exception:
        # Return an empty list on network trouble so the API still responds
        return []


def get_xrpl_client():
    """Return a simple client factory. Tests will patch this to provide a mock.

    In production this would return a configured XRPL client instance.
    """

    # Minimal local stub: raise if network calls attempted; tests patch this
    class _Stub:
        def is_connected(self):
            return False

        def get_account_info(self, account: str) -> dict:
            """Return an empty account info placeholder.

            Tests patch this when needed.
            """
            return {}

    return _Stub()
