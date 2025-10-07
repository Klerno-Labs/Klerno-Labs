from __future__ import annotations

import sqlite3
from pathlib import Path
from types import SimpleNamespace

from app import subscriptions as subs_mod
from app.subscriptions import SubscriptionTier, get_tier_details


def _make_empty_tiers_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(db_path))
    cur = con.cursor()
    # Minimal schema for the tiers table without inserting defaults
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS subscription_tiers (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            price_xrp REAL NOT NULL,
            duration_days INTEGER NOT NULL,
            features TEXT NOT NULL
        )
        """
    )
    con.commit()
    con.close()


def _insert_tier(
    db_path: Path,
    *,
    id: str,
    name: str,
    desc: str,
    price: float,
    days: int,
    features: list[str],
) -> None:
    con = sqlite3.connect(str(db_path))
    cur = con.cursor()
    cur.execute(
        """
        INSERT OR REPLACE INTO subscription_tiers
        (id, name, description, price_xrp, duration_days, features)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (id, name, desc, price, days, ",".join(features)),
    )
    con.commit()
    con.close()


def _use_temp_db_in_subs(db_path, monkeypatch):
    # Replace subscriptions module's settings with a minimal stub that points to our temp DB
    stub = SimpleNamespace(database_url=f"sqlite:///{db_path}", USE_SQLITE=True)
    monkeypatch.setattr(subs_mod, "settings", stub, raising=False)


def test_get_tier_details_cache_normalization_and_fallback(tmp_path, monkeypatch):
    # Use a temporary SQLite DB with an empty subscription_tiers table
    db_path = tmp_path / "subs_tiers_empty.db"
    _make_empty_tiers_db(db_path)

    # Point subscriptions to our temp DB via a stub settings object and clear cache
    _use_temp_db_in_subs(db_path, monkeypatch)
    if hasattr(subs_mod, "_tier_cache"):
        subs_mod._tier_cache.clear()  # type: ignore[attr-defined]

    # Request STARTER via enum -> should fallback to DEFAULT_TIERS and cache under "starter"
    t1 = get_tier_details(SubscriptionTier.STARTER)
    assert t1.id == SubscriptionTier.STARTER
    # Verify cached under normalized string key and subsequent string lookup uses cache
    assert "starter" in subs_mod._tier_cache  # type: ignore[attr-defined]

    t2 = get_tier_details("starter")
    # Should return the same object instance due to cache hit
    assert t1 is t2


def test_get_tier_details_db_row_and_unknown(tmp_path, monkeypatch):
    # Use a fresh temporary SQLite DB and insert a PROFESSIONAL row only
    db_path = tmp_path / "subs_tiers_professional.db"
    _make_empty_tiers_db(db_path)

    _insert_tier(
        db_path,
        id="professional",
        name="Professional",
        desc="Mid tier",
        price=25.0,
        days=30,
        features=["Feature A", "Feature B"],
    )

    # Point subscriptions to our temp DB via a stub settings object and clear cache
    _use_temp_db_in_subs(db_path, monkeypatch)
    if hasattr(subs_mod, "_tier_cache"):
        subs_mod._tier_cache.clear()  # type: ignore[attr-defined]

    # DB-backed tier should be returned and cached
    prof = get_tier_details("professional")
    assert prof.id == "professional"
    assert prof.name == "Professional"
    assert prof.duration_days == 30
    assert prof.features == ["Feature A", "Feature B"]
    assert "professional" in subs_mod._tier_cache  # type: ignore[attr-defined]

    # An unknown tier should raise ValueError (no default and not in DB)
    try:
        get_tier_details("unknown-tier")
        raise AssertionError("Expected ValueError for unknown tier")
    except ValueError:
        pass
