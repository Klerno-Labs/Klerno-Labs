from __future__ import annotations

import os
from datetime import datetime
from typing import Any

import requests

try:
    # Prefer app.models when available (package installed under app/)
    from app.models import Transaction  # type: ignore[no-redef]
except Exception:
    from ..models import Transaction  # type: ignore[no-redef]

BSC_API = "https://publicapi.dev/bscscan-api/api"
BSC_KEY = os.getenv("BSC_API_KEY", "").strip()


def _ts(sec: str | int) -> str:
    try:
        ts = int(sec)
        dt = datetime.utcfromtimestamp(ts)
        return dt.strftime("%Y-%m-%dT%H:%M:%S")
    except Exception:
        return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")


def fetch_account_tx(address: str, limit: int = 10) -> list[dict[str, Any]]:
    """Uses bscscan 'txlist' equivalent via publicapi.dev route."""
    params: dict[str, Any] = {
        "module": "account",
        "action": "txlist",
        "address": address,
        "startblock": 0,
        "endblock": 99999999,
        "page": 1,
        "offset": max(1, min(limit, 100)),
        "sort": "desc",
        "apikey": BSC_KEY or "free",  # publicapi.dev allows no-key; key recommended
    }
    r = requests.get(BSC_API, params=params, timeout=20)
    r.raise_for_status()
    data = r.json()
    # Both bscscan and publicapi.dev return a dict with
    # keys like {"status":"1","message":"OK","result":[...]} or similar
    return data.get("result") or []


def bsc_json_to_transactions(address: str, payload: list[dict[str, Any]]):
    out = []
    addr = (address or "").lower()
    for it in payload:
        try:
            from_addr = str(it.get("from", "")).lower()
            to_addr = str(it.get("to", "")).lower()
            # native BNB transfer value is in wei
            value_wei = int(it.get("value", 0))
            amount = value_wei / 10**18
            fee = (
                int(it.get("gasPrice", 0))
                * int(it.get("gasUsed", it.get("gas", 0) or 0))
            ) / 10**18
            if to_addr == addr:
                direction = "in"
            elif from_addr == addr:
                direction = "out"
            else:
                direction = ""
            tx = Transaction(
                tx_id=it.get("hash") or "",
                timestamp=_ts(str(it.get("timeStamp") or "0")),
                chain="BSC",
                from_addr=from_addr,
                to_addr=to_addr,
                amount=float(amount),
                symbol="BNB",
                direction=direction,
                memo="",
                fee=float(fee),
            )
            out.append(tx)
        except Exception:
            continue
    return out
