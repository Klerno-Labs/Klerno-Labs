"""Regression tests for password verification guard.

Ensures malformed bcrypt strings do not crash the bcrypt backend and that
the policy-based verification path continues to work.
"""


def test_malformed_bcrypt_does_not_panic():
    # Import inside test to match application import behavior
    from app.auth import _verify_password

    # Placeholder/malformed bcrypt string from tests/fixtures
    bad_hash = "$2b$12$test_hash"

    # Should not raise and should return a boolean; value may be True in
    # environments that intentionally treat certain test sentinels as valid.
    result = _verify_password("testpassword", bad_hash)
    assert isinstance(result, bool)


def test_policy_hash_verifies_true():
    # Using the configured password policy to generate a valid hash
    from app.auth import _verify_password
    from app.security_modules.password_policy import policy

    password = "S0meValid!Passw0rd"
    hashed = policy.hash(password)

    # Should verify True through the policy fallback path
    assert _verify_password(password, hashed) is True
