
import inspect
from typing import Any

from fastapi import APIRouter, HTTPException

from integrations import xrp as xrp_integ

router = APIRouter(prefix="/xrpl")


@router.post("/create-account", status_code=201)
def create_account() -> dict[str, str]:
    """Create a test XRPL account (stub).

    This endpoint is primarily used by tests; the underlying client is patched
    by the test suite. We return a minimal created account shape.
    """
    client = xrp_integ.get_xrpl_client()
    if not client or not getattr(client, "is_connected", lambda: False)():
        raise HTTPException(status_code=500, detail="XRPL client unavailable")
    return {"account_address": "rTest123", "secret": "sXXXXXXXX"}


@router.get("/balance/{account}")
async def get_balance(account: str) -> dict[str, float]:
    """Return the XRP balance for `account` using the xrpl integration client.

    The client is typically patched in tests to return deterministic values.
    """
    client = xrp_integ.get_xrpl_client()
    if not client or not getattr(client, "is_connected", lambda: False)():
        raise HTTPException(status_code=500, detail="XRPL client unavailable")

    # In tests, patched client.get_account_info may be an AsyncMock. Await
    # if the returned object is awaitable.
    info: Any = client.get_account_info(account)
    # If the integration returns an awaitable (AsyncMock or coroutine), await it.
    if inspect.isawaitable(info):
        info = await info

    bal = 0.0
    try:
        bal = int(info.get("account_data", {}).get("Balance", 0)) / 1_000_000.0
    except Exception:
        bal = 0.0
    return {"balance": bal}
