import os
import sys
from pathlib import Path

import psycopg


def main():
    if len(sys.argv) < 2:
        print("Usage: vendor_apply_sql_migration.py <path-to-sql>")
        sys.exit(1)
    sql_path = sys.argv[1]
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL not set in environment")
        sys.exit(1)
    if not Path(sql_path).exists():
        print(f"ERROR: SQL file not found: {sql_path}")
        sys.exit(1)

    sql_text = Path(sql_path).read_text(encoding="utf-8")

    # Drizzle inserts statement-breakpoint markers; replace with a semicolon+newline boundary
    sql_text = sql_text.replace("--> statement-breakpoint", "")

    # Split into individual statements on semicolons. This is naive but sufficient for our simple migration file.
    # It avoids issues with drivers that don't accept multiple statements in a single execute.
    statements = [s.strip() for s in sql_text.split(";")]
    statements = [s for s in statements if s]

    try:
        with psycopg.connect(db_url, autocommit=True) as conn, conn.cursor() as cur:
            for stmt in statements:
                # Execute raw SQL since this is a migration script reading from trusted files
                cur.execute(stmt)  # type: ignore[arg-type]
        print("Applied migration successfully from:", sql_path)
    except Exception as e:
        print("ERROR applying migration:", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
