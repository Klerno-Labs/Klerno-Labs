"""Quick smoke test for password hashing and rotation helpers.

Run from the repo root with the project's venv active.
"""

from app import security_session as sec


def run() -> None:
    pw = "correct horse battery staple"
    h = sec.hash_pw(pw)
    _ok, new = sec.verify_and_maybe_rehash(pw, h)
    if new:
        pass


if __name__ == "__main__":
    run()
