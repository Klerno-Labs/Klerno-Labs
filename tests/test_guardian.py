from datetime import UTC, datetime

from app.guardian import score_risk
from app.models import Transaction


def test_large_outgoing_risk():
    tx = Transaction(
        tx_id="1",
        timestamp=datetime.now(UTC),
        chain="XRP",
        from_addr="rAlice",
        to_addr="rBob",
        amount=6000,
        symbol="XRP",
        direction="out",
    )
    score, flags = score_risk(tx)
    assert score > 0
    assert "large_outgoing" in flags
