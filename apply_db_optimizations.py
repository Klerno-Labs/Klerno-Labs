#!/usr/bin/env python3
"""Apply database optimizations."""

import json
import sqlite3
from pathlib import Path


def apply_optimizations() -> None:
    """Apply database optimization queries."""
    with Path("database_validation_report.json").open() as f:
        report = json.load(f)

    conn = sqlite3.connect("./data/klerno.db")
    cursor = conn.cursor()

    applied = 0
    for query in report["optimization_queries"]:
        try:
            cursor.execute(query)
            applied += 1
        except Exception:
            pass

    conn.commit()
    conn.close()


if __name__ == "__main__":
    apply_optimizations()
