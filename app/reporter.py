from io import StringIO

import pandas as pd

from .models import ReportSummary, TaggedTransaction


def to_dataframe(txs: list[TaggedTransaction]) -> pd.DataFrame:
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
