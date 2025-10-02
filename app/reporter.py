from io import StringIO
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    # Use Any so mypy doesn't require pandas to be installed in the dev env
    pd: Any
else:
    pd = None

from .models import ReportSummary, TaggedTransaction


def _ensure_pandas() -> None:
    if "pd" in globals():
        return
    try:
        import importlib

        pd = importlib.import_module("pandas")
        globals()["pd"] = pd
    except ImportError as e:
        raise ImportError(
            "pandas is required to convert transactions to DataFrame"
        ) from e


def to_dataframe(txs: list[TaggedTransaction]) -> Any:
    # Import locally to avoid requiring pandas at module import time.
    _ensure_pandas()
    pd = globals().get("pd")
    if pd is None:
        raise ImportError("pandas is required to convert transactions to DataFrame")

    return pd.DataFrame([t.model_dump() for t in txs])


def summary(txs: list[TaggedTransaction]) -> ReportSummary:
    from decimal import Decimal

    # Ensure sums produce Decimal when no items present by providing Decimal start
    total_in = sum((t.amount for t in txs if t.direction == "in"), Decimal("0"))
    total_out = sum((t.amount for t in txs if t.direction == "out"), Decimal("0"))
    fees = sum((t.fee or Decimal("0") for t in txs), Decimal("0"))

    # Counts
    count_in = sum(1 for t in txs if t.direction == "in")
    count_out = sum(1 for t in txs if t.direction == "out")

    # Suspicious count is computed elsewhere; compute net here
    net = total_in - total_out

    return ReportSummary(
        count_in=count_in,
        count_out=count_out,
        total_in=total_in,
        total_out=total_out,
        total_fees=fees,
        net=net,
    )


def csv_export(txs: list[TaggedTransaction]) -> str:
    df = to_dataframe(txs)
    buf = StringIO()
    df.to_csv(buf, index=False)
    return buf.getvalue()
