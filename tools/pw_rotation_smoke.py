"""Quick smoke test for password hashing and rotation helpers.

Run from the repo root with the project's venv active.
"""

from app import security_session as sec


def run():
    pw = "correct horse battery staple"
    h = sec.hash_pw(pw)
    print("Hash:", h[:60])
    ok, new = sec.verify_and_maybe_rehash(pw, h)
    print("Verified:", ok)
    print("New hash returned:", bool(new))
    if new:
        print("New hash:", new[:60])


if __name__ == "__main__":
    run()
