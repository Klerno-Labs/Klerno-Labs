import importlib
from app import security_session as sec


def test_verify_and_maybe_rehash_forces_rehash(monkeypatch):
    pw = "s3cret-pass"
    # Create a current hash using the module helper
    current_hash = sec.hash_pw(pw)

    # Force the CryptContext to indicate the hash needs updating and return a known new hash
    monkeypatch.setattr(sec._pwd, "needs_update", lambda _h: True)
    monkeypatch.setattr(sec._pwd, "hash", lambda _pw: "__NEW_HASH__")

    ok, new = sec.verify_and_maybe_rehash(pw, current_hash)
    assert ok is True
    assert new == "__NEW_HASH__"
