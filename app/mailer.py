# app / mailer.py
import os
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    # Treat sendgrid types as Any in environments where stubs are missing.
    # Use a simple Any assignment instead of a type: ignore comment which mypy
    # can sometimes mark as unused.
    SendGridAPIClient: Any

_SENDGRID_KEY = os.getenv("SENDGRID_API_KEY")
FROM_EMAIL = os.getenv("SENDGRID_FROM")
FROM_NAME = os.getenv("SENDGRID_NAME", "Klerno Labs")


_cached_sg: Any = None


def _get_sendgrid_client():
    """Create and cache a SendGrid client on first use.

    Import SendGrid lazily so importing this module doesn't fail when the
    package or environment variable is not present. Raises a clear
    RuntimeError if the API key is missing at call time.
    """
    global _cached_sg
    if _cached_sg is None:
        key = os.getenv("SENDGRID_API_KEY") or _SENDGRID_KEY
        if not key:
            raise RuntimeError(
                "SendGrid API key not configured. Set SENDGRID_API_KEY to use mailer"
            )
    # Import lazily to avoid import-time dependency on sendgrid
    import importlib

    _sendgrid_module = importlib.import_module("sendgrid")
    _cached_sg = _sendgrid_module.SendGridAPIClient(key)
    return _cached_sg


def send_email(to_email: str, subject: str, content: str):
    """Send a simple email using SendGrid.

    This function validates that a sender address is configured and that a
    SendGrid client can be created. It returns the HTTP status code from
    the SendGrid API on success, and raises a RuntimeError on misconfiguration.
    """
    if not FROM_EMAIL:
        raise RuntimeError(
            "Sender address not configured. Set SENDGRID_FROM to use mailer"
        )

    sg = _get_sendgrid_client()

    # Import Mail class lazily as well
    import importlib

    sg_helpers = importlib.import_module("sendgrid.helpers.mail")
    Mail = sg_helpers.Mail

    message = Mail(
        from_email=(FROM_EMAIL, FROM_NAME),
        to_emails=to_email,
        subject=subject,
        plain_text_content=content,
        html_content=f"<p>{content}</p>",
    )
    response = sg.send(message)
    return response.status_code
