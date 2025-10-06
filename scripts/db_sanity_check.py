import os

import psycopg


def main():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL not set")
        raise SystemExit(1)
    with psycopg.connect(db_url) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema='public' ORDER BY table_name"
        )
        tables = [r[0] for r in cur.fetchall()]
        print("tables:", tables)
        cur.execute(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_schema='public' AND table_name='notes' "
            "ORDER BY ordinal_position"
        )
        cols = cur.fetchall()
        print("notes columns:", cols)


if __name__ == "__main__":
    main()
