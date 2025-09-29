from scripts import check_prod_readiness as cpr


def test_non_production_no_jwt(monkeypatch, capsys):
    # No APP_ENV (defaults to non-production) and no JWT_SECRET
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("JWT_SECRET", raising=False)
    assert cpr.check_env_vars() is True
    assert cpr.check_secret_strength() is True
    captured = capsys.readouterr()
    assert "[WARN]" in captured.out


def test_production_missing_jwt(monkeypatch, capsys):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("JWT_SECRET", raising=False)
    assert cpr.check_env_vars() is False
    assert cpr.check_secret_strength() is False
    captured = capsys.readouterr()
    assert "[FAIL]" in captured.out


def test_weak_secret_detected(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("JWT_SECRET", "changeme")
    # Avoid importing the app (which may have side effects) by stubbing
    monkeypatch.setattr(cpr, "check_import_app", lambda: True)
    problems = cpr.run_checks()
    assert any("Secret strength" in p for p in problems)


def test_run_checks_success_and_main_exit(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("JWT_SECRET", "A" * 32)
    monkeypatch.setenv("DATABASE_URL", "postgres://user:pass@localhost/db")
    # Stub import check to avoid import-time side effects
    monkeypatch.setattr(cpr, "check_import_app", lambda: True)
    problems = cpr.run_checks()
    assert problems == []
    # main returns 0 on success
    rc = cpr.main()
    assert rc == 0
