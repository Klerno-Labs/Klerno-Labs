# app / notifications.py
import os

import httpx


async def slack_notify(text: str) -> dict:
    """Send a Slack notification if SLACK_WEBHOOK_URL is configured.

    The webhook URL is read at call time so importing this module doesn't
    perform environment-dependent behavior.
    """
    webhook = (os.getenv("SLACK_WEBHOOK_URL") or "").strip()
    if not webhook:
        return {"sent": False, "reason": "no webhook configured"}

    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.post(webhook, json={"text": text})
        return {"sent": 200 <= r.status_code < 300, "status": r.status_code}
