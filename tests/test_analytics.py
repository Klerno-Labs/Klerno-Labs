"""Tests for advanced analytics functionality."""

import pytest

from app.analytics import AdvancedAnalytics, AnalyticsMetrics, InsightsEngine


def test_empty_analytics() -> None:
    """Test analytics with no data."""
    # Clear transactions table for this test (use correct table name)
    import sqlite3

    from app import store

    conn = sqlite3.connect(store.DB_PATH)
    conn.execute("DELETE FROM txs")  # Changed from 'transactions' to 'txs'
    conn.commit()
    conn.close()

    # Clear ALL cache entries to ensure fresh data
    store._cache.clear()
    store._cache_expiry.clear()
    store._clear_cache_pattern("list_all")

    try:
        analytics = AdvancedAnalytics()
        metrics = analytics.generate_comprehensive_metrics(days=30)

        assert metrics.total_transactions == 0
        assert metrics.total_volume == 0.0
        assert metrics.avg_risk_score == 0.0
        assert metrics.high_risk_count == 0
        assert metrics.unique_addresses == 0
        assert len(metrics.top_risk_addresses) == 0
        assert len(metrics.risk_trend) == 0
    finally:
        # Tests should be isolated, no need to restore data
        pass


def test_risk_bucket_calculation() -> None:
    """Test risk bucket categorization."""
    analytics = AdvancedAnalytics()

    # Test risk thresholds
    assert analytics.risk_thresholds["low"] == 0.33
    assert analytics.risk_thresholds["medium"] == 0.66
    assert analytics.risk_thresholds["high"] == 1.0


def test_insights_generation() -> None:
    """Test AI insights generation."""
    insights_engine = InsightsEngine()

    # Test with high risk metrics
    high_risk_metrics = AnalyticsMetrics(
        total_transactions=100,
        total_volume=2000000.0,
        avg_risk_score=0.85,
        high_risk_count=25,
        medium_risk_count=30,
        low_risk_count=45,
        unique_addresses=50,
        top_risk_addresses=[],
        risk_trend=[],
        category_distribution={},
        hourly_activity=[],
        network_analysis={},
        anomaly_score=0.15,
    )

    insights = insights_engine.generate_insights(high_risk_metrics)

    # Should generate high risk warning
    high_risk_insights = [i for i in insights if i["type"] == "warning"]
    assert len(high_risk_insights) > 0

    # Should have high priority insights
    high_priority_insights = [i for i in insights if i["priority"] == "high"]
    assert len(high_priority_insights) > 0


def test_insights_low_risk() -> None:
    """Test insights with low risk metrics."""
    insights_engine = InsightsEngine()

    low_risk_metrics = AnalyticsMetrics(
        total_transactions=100,
        total_volume=50000.0,
        avg_risk_score=0.15,
        high_risk_count=2,
        medium_risk_count=10,
        low_risk_count=88,
        unique_addresses=80,
        top_risk_addresses=[],
        risk_trend=[],
        category_distribution={},
        hourly_activity=[],
        network_analysis={},
        anomaly_score=0.02,
    )

    insights = insights_engine.generate_insights(low_risk_metrics)

    # Should not generate high risk warnings
    high_risk_insights = [i for i in insights if "High Average Risk" in i["title"]]
    assert len(high_risk_insights) == 0


def test_network_hub_insights() -> None:
    """Test network hub detection insights."""
    insights_engine = InsightsEngine()

    metrics_with_hub = AnalyticsMetrics(
        total_transactions=100,
        total_volume=50000.0,
        avg_risk_score=0.25,
        high_risk_count=5,
        medium_risk_count=15,
        low_risk_count=80,
        unique_addresses=50,
        top_risk_addresses=[],
        risk_trend=[],
        category_distribution={},
        hourly_activity=[],
        network_analysis={
            "hub_addresses": [{"address": "rHub123...", "connection_count": 25}],
        },
        anomaly_score=0.05,
    )

    insights = insights_engine.generate_insights(metrics_with_hub)

    # Should generate network hub insight
    hub_insights = [i for i in insights if "Network Hub" in i["title"]]
    assert len(hub_insights) > 0


if __name__ == "__main__":
    pytest.main([__file__])
