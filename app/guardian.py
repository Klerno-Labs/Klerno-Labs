from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal
from typing import Any

SUSPICIOUS_WORDS = {
    "scam",
    "phish",
    "hack",
    "fraud",
    "ransom",
    "malware",
    "blackmail",
    "mixer",
    "tornado",
    "sanction",
    "darknet",
}


def _as_decimal(x, default: str = "0") -> Decimal:
    if isinstance(x, Decimal):
        return x
    try:
        return Decimal(str(x))
    except Exception:
        return Decimal(default)


def _norm(s: str | None) -> str:
    return (s or "").strip().lower()


def _get(tx, name: str, default=None) -> None:
    if hasattr(tx, name):
        return getattr(tx, name)
    if isinstance(tx, dict[str, Any]):
        return tx.get(name, default)
    return default


def score_risk(tx) -> tuple[float, list[str]]:
    """Returns (score, flags). Score is clamped to [0, 1].
    Flags explain which signals contributed; useful for tests & auditing.
    """
    memo = _norm(_get(tx, "memo", ""))
    amount = _as_decimal(_get(tx, "amount", 0))
    fee = _as_decimal(_get(tx, "fee", 0))
    direction = _norm(_get(tx, "direction", ""))
    is_internal = bool(_get(tx, "is_internal", False))

    tags: Iterable[str] = _get(tx, "tags", []) or []
    tags = {_norm(t) for t in tags}

    score = Decimal("0.10")
    flags: list[str] = []

    # Direction & magnitude (keeps your thresholds; adds flags)
    if direction in {"out", "outgoing", "debit"}:
        flags.append("outgoing")
        mag = abs(amount)
        if mag > 0:
            score += Decimal("0.10")
        if mag > 100:
            score += Decimal("0.10")
            flags.append("medium_outgoing")
        if mag > 1000:
            score += Decimal("0.15")
            flags.append("large_outgoing")
        if mag > 10000:
            score += Decimal("0.15")
            flags.append("very_large_outgoing")
    elif direction in {"in", "incoming", "credit"}:
        flags.append("incoming")
        score -= Decimal("0.05")

    # Fee pressure
    if fee > 0:
        score += Decimal("0.05")
        flags.append("fee_present")
        if amount != 0:
            ratio = (fee / abs(amount)) if abs(amount) > 0 else Decimal(0)
            if ratio > Decimal("0.01"):
                score += Decimal("0.05")
                flags.append("high_fee_ratio")
            if ratio > Decimal("0.05"):
                score += Decimal("0.10")
                flags.append("very_high_fee_ratio")

    # Suspicious memo keywords
    if memo:
        hits = sum(1 for w in SUSPICIOUS_WORDS if w in memo)
        if hits:
            score += Decimal("0.20") + Decimal("0.05") * Decimal(hits)
            flags.append("suspicious_memo")

    # Tag - based adjustments
    if "sanctioned" in tags or "mixer" in tags:
        score += Decimal("0.20")
        flags.append("sanctioned_or_mixer")

    # Internal transfers reduce risk
    if is_internal:
        score -= Decimal("0.25")
        flags.append("internal_transfer")

    # Clamp to [0, 1]
    if score < 0:
        score = Decimal(0)
    if score > 1:
        score = Decimal(1)

    return float(score), flags


# Back - compat: old callers that expect just a float can use this.


def score_risk_value(tx) -> float:
    return score_risk(tx)[0]


# Backwards-compatible GuardianEngine expected by tests
class GuardianEngine:
    """Minimal Guardian engine used by unit tests.

    Provides async anomaly detection and simple pattern recognition.
    """

    def __init__(self) -> None:
        pass

    async def detect_anomalies(
        self, transactions: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        # Very small anomaly detector: flag txs with amount far above median
        amounts = [abs(Decimal(str(t.get("amount", 0)))) for t in transactions]
        if not amounts:
            return []
        median = sorted(amounts)[len(amounts) // 2]
        anomalies: list[dict[str, Any]] = []
        for t in transactions:
            try:
                if Decimal(str(t.get("amount", 0))) > median * 10:
                    anomalies.append(t)
            except Exception:
                # ignore malformed entries
                continue
        return anomalies

    async def detect_patterns(
        self, transactions: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        # Return a list[Any] of pattern dicts used by tests. Detect simple
        # structured layering: repeated transfers of the same amount to
        # different accounts.
        total = sum(float(t.get("amount", 0)) for t in transactions)
        patterns: list[dict[str, Any]] = []

        # naive detection: if multiple transactions have same amount and
        # different recipients, flag as structured_layering
        amounts_map: dict[float, set[str]] = {}
        for t in transactions:
            amt = float(t.get("amount", 0))
            to_acc = str(t.get("to_account") or t.get("to") or "")
            amounts_map.setdefault(amt, set()).add(to_acc)

        for amt, recipients in amounts_map.items():
            if len(recipients) >= 3:
                patterns.append(
                    {
                        "type": "structured_layering",
                        "amount": amt,
                        "count": len(recipients),
                    },
                )

        # Always include a summary pattern
        patterns.append({"type": "summary", "count": len(transactions), "total": total})
        return patterns

    # Backwards-compatible instance method name expected by older code/tests
    async def analyze_patterns(
        self, transactions: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        return await self.detect_patterns(transactions)


# Backwards-compatible name expected by older tests
async def analyze_patterns(transactions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    # Use a cached engine to avoid allocating an engine on each call.
    engine = _get_guardian_engine()
    return await engine.detect_patterns(transactions)


_guardian_instance: GuardianEngine | None = None


def _get_guardian_engine() -> GuardianEngine:
    """Return cached GuardianEngine; create lazily on first use."""
    global _guardian_instance
    if _guardian_instance is None:
        _guardian_instance = GuardianEngine()
    return _guardian_instance
