# app / integrations / bscscan.py
from __future__ import annotations

import os
import time
from typing import Any

import requests

try:
    from app.models import Transaction
except Exception:
    from ..models import Transaction

BASE_URL = "https://api.bscscan.com/api"
DEFAULT_LIMIT = 25


def _api_key(explicit: str | None = None) -> str:
    # Prefer explicit key, else env
    return (explicit or os.getenv("BSC_API_KEY") or "").strip()


def _get(params: dict[str, Any], api_key: str | None) -> dict[str, Any]:
    p = dict(params)
    key = _api_key(api_key)
    if key:
        p["apikey"] = key
    r = requests.get(BASE_URL, params=p, timeout=15)
    r.raise_for_status()
    data = r.json()
    # BscScan returns {"status":"1","message":"OK","result":[...]} on success
    return data


def _wei_to_bnb(x: str) -> float:
    try:
        return int(x) / 1e18
    except Exception:
        return 0.0


def _scale(value_str: str, decimals: str) -> float:
    try:
        d = int(decimals or "18")
        return int(value_str) / (10**d)
    except Exception:
        return 0.0


def _ts_to_iso(sec_str: str) -> str:
    try:
        sec = int(sec_str)
        return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(sec))
    except Exception:
        return ""


def fetch_account_tx_bscscan(
    address: str,
    *,
    limit: int = DEFAULT_LIMIT,
    api_key: str | None = None,
) -> dict[str, Any]:
    """
    Fetch recent normal, token, and internal transactions for an address.
    Returns raw payloads as dict: {
        "normal": [...], "token": [...], "internal": [...]
    }
    """
    offset = max(1, min(limit, 10000))
    common = {
        "address": address,
        "startblock": 0,
        "endblock": 99999999,
        "page": 1,
        "offset": offset,
        "sort": "desc",
    }

    normal = (
        _get({"module": "account", "action": "txlist", **common}, api_key).get(
            "result", []
        )
        or []
    )
    tok_params = {"module": "account", "action": "tokentx", **common}
    token = _get(tok_params, api_key).get("result", []) or []

    int_params = {"module": "account", "action": "txlistinternal", **common}
    internal = _get(int_params, api_key).get("result", []) or []

    return {"normal": normal, "token": token, "internal": internal}


def bscscan_json_to_transactions(
    account: str,
    payload: dict[str, Any],
) -> list[Transaction]:
    """
    Normalize BscScan payloads into a List[Transaction].
    Handles native BNB sends, token transfers, and internal txs.
    """
    acct = (account or "").lower().strip()
    items: list[Transaction] = []
    seen = set()

    # ---- Normal (native BNB sends)
    for it in payload.get("normal", []):
        try:
            key = ("normal", it.get("hash"))
            if key in seen:
                continue
            seen.add(key)

            from_addr = (it.get("from") or "").lower()
            to_addr = (it.get("to") or "").lower()
            if to_addr == acct:
                direction = "in"
            elif from_addr == acct:
                direction = "out"
            else:
                direction = "other"

            fee = 0.0
            try:
                gas_price = int(it.get("gasPrice") or "0")
                gas_used = int(it.get("gasUsed") or "0")
                fee = (gas_price * gas_used) / 1e18
            except Exception:
                fee = 0.0

            items.append(
                Transaction(
                    tx_id=it.get("hash") or "",
                    timestamp=_ts_to_iso(it.get("timeStamp") or ""),
                    chain="BSC",
                    from_addr=it.get("from") or "",
                    to_addr=it.get("to") or "",
                    amount=_wei_to_bnb(it.get("value") or "0"),
                    symbol="BNB",
                    direction=direction,
                    memo=(it.get("functionName") or "").strip() or "",
                    fee=fee,
                )
            )
        except Exception:
            continue

    # ---- Token transfers (BEP - 20)
    for it in payload.get("token", []):
        try:
            key = ("token", it.get("hash"), it.get("logIndex"))
            if key in seen:
                continue
            seen.add(key)

            from_addr = (it.get("from") or "").lower()
            to_addr = (it.get("to") or "").lower()
            if to_addr == acct:
                direction = "in"
            elif from_addr == acct:
                direction = "out"
            else:
                direction = "other"

            amount = _scale(
                it.get("value") or "0", it.get("tokenDecimal") or "18"
            )
            symbol = (it.get("tokenSymbol") or "").upper() or "TOKEN"

            items.append(
                Transaction(
                    tx_id=it.get("hash") or "",
                    timestamp=_ts_to_iso(it.get("timeStamp") or ""),
                    chain="BSC",
                    from_addr=it.get("from") or "",
                    to_addr=it.get("to") or "",
                    amount=amount,
                    symbol=symbol,
                    direction=direction,
                    memo=f"{it.get('tokenName') or ''} ({symbol})",
                    fee=0.0,  # fee is on the parent tx; accounted in "normal"
                )
            )
        except Exception:
            continue

    # ---- Internal tx (value transfers triggered by contracts)
    for it in payload.get("internal", []):
        try:
            key = ("internal", it.get("hash"), it.get("traceId"))
            if key in seen:
                continue
            seen.add(key)

            from_addr = (it.get("from") or "").lower()
            to_addr = (it.get("to") or "").lower()
            if to_addr == acct:
                direction = "in"
            elif from_addr == acct:
                direction = "out"
            else:
                direction = "other"

            items.append(
                Transaction(
                    tx_id=it.get("hash") or "",
                    timestamp=_ts_to_iso(it.get("timeStamp") or ""),
                    chain="BSC",
                    from_addr=it.get("from") or "",
                    to_addr=it.get("to") or "",
                    amount=_wei_to_bnb(it.get("value") or "0"),
                    symbol="BNB",
                    direction=direction,
                    memo="internal",
                    fee=0.0,
                )
            )
        except Exception:
            continue

    # newest first
    items.sort(key=lambda x: x.timestamp or "", reverse=True)
    return items
