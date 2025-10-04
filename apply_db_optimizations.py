#!/usr/bin/env python3
"""Apply database optimizations."""

import json
import sqlite3


def apply_optimizations():
    """Apply database optimization queries."""
    with open("database_validation_report.json") as f:
        report = json.load(f)

    conn = sqlite3.connect("./data/klerno.db")
    cursor = conn.cursor()

    applied = 0
    for query in report["optimization_queries"]:
        try:
            cursor.execute(query)
            applied += 1
            print(f"✅ Applied: {query}")
        except Exception as e:
            print(f"❌ Failed: {query} - {e}")

    conn.commit()
    conn.close()
    print(
        f"\n🎯 Applied {applied}/{len(report['optimization_queries'])} optimization queries"
    )


if __name__ == "__main__":
    apply_optimizations()
