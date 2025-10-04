# Debug helper: seed a temp sqlite DB and verify password hashing/verification
import os
import sqlite3
import sys
import tempfile
from pathlib import Path

# ensure project import path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# create temp DB
with tempfile.NamedTemporaryFile(
    prefix="klerno_test_debug_",
    suffix=".db",
    delete=False,
) as temp_db:
    db_path = temp_db.name

# set env to force store to use this db; set DATABASE_URL so modules that
# load .env won't overwrite our selection (dotenv.load_dotenv uses override=False)
os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
os.environ["DB_PATH"] = db_path

print("DEBUG: DB_PATH ->", os.environ["DB_PATH"])

# create legacy users table
con = sqlite3.connect(db_path)
cur = con.cursor()
cur.execute(
    """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    email TEXT UNIQUE,
    hashed_password TEXT,
    is_active INTEGER DEFAULT 1,
    is_admin INTEGER DEFAULT 0
)
""",
)
con.commit()
con.close()

# import hashing from app
from app import store
from app.security_session import hash_pw, verify_pw

pw = "testpassword"
pw_hash = hash_pw(pw)
print("DEBUG: generated hash prefix:", pw_hash[:4])

# Insert user
con = sqlite3.connect(db_path)
cur = con.cursor()
cur.execute(
    "INSERT OR REPLACE INTO users (id, email, hashed_password, is_active, is_admin) VALUES (?, ?, ?, ?, ?)",
    (1, "test@example.com", pw_hash, 1, 0),
)
con.commit()
con.close()

# Direct DB introspection to confirm contents
print("\nDEBUG: Raw DB contents (sqlite3 query)")
con = sqlite3.connect(db_path)
cur = con.cursor()
try:
    cur.execute("SELECT id, email, hashed_password, is_active, is_admin FROM users")
    rows = cur.fetchall()
    for r in rows:
        print("row ->", r)
except Exception as e:
    print("raw select failed:", type(e).__name__, str(e))
finally:
    con.close()

# Read via store
user = store.get_user_by_email("test@example.com")
print("\nstore.get_user_by_email ->", user)
print("store returned user keys:", list(user.keys()) if user else None)
if user and user.get("password_hash"):
    ph = user.get("password_hash")
    if ph:
        # cast to str for static checkers; in runtime ph should be a str
        from typing import cast

        ph_str = cast("str", ph)
        print("stored password_hash (prefix):", ph_str[:8])
        ok = verify_pw(pw, ph_str)
        print("verify_pw result:", ok)

# cleanup
from contextlib import suppress

with suppress(Exception):
    Path(db_path).unlink()
