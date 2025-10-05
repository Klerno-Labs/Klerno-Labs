"""Advanced Analytics Module for Klerno Labs
Provides enhanced analytics, insights, and dashboard functionality.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any


def _ensure_numpy() -> None:
    if "np" in globals():
        return
    try:
        import importlib

        np = importlib.import_module("numpy")
        globals()["np"] = np
    except ImportError as e:
        msg = "numpy is required for analytics computations"
        raise RuntimeError(msg) from e
    except Exception:
        raise


from . import store


def _ensure_pandas() -> None:
    """Import pandas into module globals on first use.

    This defers heavy import-time work and avoids circular-import issues
    that can occur during test collection when import order is sensitive.
    """
    if "pd" in globals():
        return
    try:
        import importlib

        pd = importlib.import_module("pandas")
        globals()["pd"] = pd
    except ImportError as e:
        msg = "pandas is required for analytics features"
        raise RuntimeError(msg) from e
    except Exception:
        raise


if TYPE_CHECKING:
    # Use Any for heavy optional dependencies so mypy doesn't require their
    # presence in developer environments where installing them is undesirable.
    np: Any
    pd: Any
else:
    np = None
    pd = None


@dataclass
class AnalyticsMetrics:
    """Enhanced analytics metrics structure."""

    total_transactions: int
    total_volume: float
    avg_risk_score: float
    high_risk_count: int
    medium_risk_count: int
    low_risk_count: int
    unique_addresses: int
    top_risk_addresses: list[dict[str, Any]]
    risk_trend: list[dict[str, Any]]
    category_distribution: dict[str, int]
    hourly_activity: list[dict[str, Any]]
    network_analysis: dict[str, Any]
    anomaly_score: float


class AdvancedAnalytics:
    """Advanced analytics engine for transaction analysis."""

    def __init__(self) -> None:
        self.risk_thresholds = {"low": 0.33, "medium": 0.66, "high": 1.0}

    def generate_comprehensive_metrics(self, days: int = 30) -> AnalyticsMetrics:
        """Generate comprehensive analytics metrics for the dashboard."""
        # Get data from the last N days
        cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=days)
        rows = store.list_all(limit=50000)

        # If there are no rows, return empty metrics without importing pandas
        if not rows:
            return self._empty_metrics()

        # Import pandas only when data is present and a DataFrame is required
        _ensure_pandas()
        df = pd.DataFrame(rows)
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        # Use a direct function reference to keep the line short
        df["risk_score"] = df.apply(self._get_risk_score, axis=1)
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)

        # Filter by date range
        recent_df = df[df["timestamp"] >= cutoff] if not df.empty else df

        if recent_df.empty:
            return self._empty_metrics()

        # Precompute commonly-used metrics to keep call-site short
        total_transactions = len(recent_df)
        total_volume = float(recent_df["amount"].sum())
        avg_risk_score = float(recent_df["risk_score"].mean())
        rt = self.risk_thresholds
        high_risk_count = int((recent_df["risk_score"] >= rt["medium"]).sum())
        medium_risk_count = int(
            (
                (recent_df["risk_score"] >= rt["low"])
                & (recent_df["risk_score"] < rt["medium"])
            ).sum(),
        )
        low_risk_count = int((recent_df["risk_score"] < rt["low"]).sum())

        return AnalyticsMetrics(
            total_transactions=total_transactions,
            total_volume=total_volume,
            avg_risk_score=avg_risk_score,
            high_risk_count=high_risk_count,
            medium_risk_count=medium_risk_count,
            low_risk_count=low_risk_count,
            unique_addresses=self._count_unique_addresses(recent_df),
            top_risk_addresses=self._get_top_risk_addresses(recent_df),
            risk_trend=self._calculate_risk_trend(recent_df),
            category_distribution=self._get_category_distribution(recent_df),
            hourly_activity=self._get_hourly_activity(recent_df),
            network_analysis=self._analyze_network_patterns(recent_df),
            anomaly_score=self._calculate_anomaly_score(recent_df),
        )

    def _get_risk_score(self, row: Any) -> float:
        """Extract risk score from row with fallback."""
        _ensure_pandas()
        try:
            score = row.get("risk_score", row.get("score", 0))
            if pd.isna(score):
                return 0.0
            return float(score)
        except (ValueError, TypeError):
            return 0.0

    def _count_unique_addresses(self, df: Any) -> int:
        """Count unique addresses in the dataset."""
        _ensure_pandas()
        addresses = set()
        for _, row in df.iterrows():
            if row.get("from_addr"):
                addresses.add(row["from_addr"])
            if row.get("to_addr"):
                addresses.add(row["to_addr"])
        return len(addresses)

    def _get_top_risk_addresses(self, df: Any, limit: int = 10) -> list[dict[str, Any]]:
        """Get top risk addresses with their metrics."""
        _ensure_pandas()
        _ensure_numpy()
        address_metrics = {}

        for _, row in df.iterrows():
            for addr_field in ["from_addr", "to_addr"]:
                addr = row.get(addr_field)
                if not addr:
                    continue

                if addr not in address_metrics:
                    address_metrics[addr] = {
                        "address": addr,
                        "transaction_count": 0,
                        "total_volume": 0,
                        "avg_risk": 0,
                        "max_risk": 0,
                        "risk_scores": [],
                    }

                metrics = address_metrics[addr]
                metrics["transaction_count"] += 1
                metrics["total_volume"] += float(row.get("amount", 0))
                risk_score = self._get_risk_score(row)
                metrics["risk_scores"].append(risk_score)
                metrics["max_risk"] = max(metrics["max_risk"], risk_score)

        # Calculate averages and sort by risk
        for metrics in address_metrics.values():
            if metrics["risk_scores"]:
                metrics["avg_risk"] = np.mean(metrics["risk_scores"])
            del metrics["risk_scores"]  # Remove raw scores to save space

        # Sort by average risk score and return top addresses
        sorted_addresses = sorted(
            address_metrics.values(),
            key=lambda x: x["avg_risk"],
            reverse=True,
        )

        return sorted_addresses[:limit]

    def _calculate_risk_trend(self, df: Any) -> list[dict[str, Any]]:
        """Calculate risk trend over time."""
        _ensure_pandas()
        if df.empty:
            return []

        # Group by day and calculate daily metrics
        df["date"] = df["timestamp"].dt.date
        daily_metrics = (
            df.groupby("date")
            .agg({"risk_score": ["mean", "max", "count"], "amount": "sum"})
            .reset_index()
        )

        daily_metrics.columns = [
            "date",
            "avg_risk",
            "max_risk",
            "transaction_count",
            "total_volume",
        ]

        trend = []
        for _, row in daily_metrics.iterrows():
            trend.append(
                {
                    "date": row["date"].isoformat(),
                    "avg_risk": float(row["avg_risk"]),
                    "max_risk": float(row["max_risk"]),
                    "transaction_count": int(row["transaction_count"]),
                    "total_volume": float(row["total_volume"]),
                },
            )

        return sorted(trend, key=lambda x: x["date"])

    def _get_category_distribution(self, df: Any) -> dict[str, int]:
        """Get distribution of transaction categories."""
        _ensure_pandas()
        if "category" not in df.columns:
            return {"unknown": len(df)}

        return df["category"].fillna("unknown").value_counts().to_dict()

    def _get_hourly_activity(self, df: Any) -> list[dict[str, Any]]:
        """Analyze transaction activity by hour of day."""
        _ensure_pandas()
        if df.empty:
            return []

        df["hour"] = df["timestamp"].dt.hour
        hourly_stats = (
            df.groupby("hour")
            .agg({"risk_score": "mean", "amount": "sum"})
            .reset_index()
        )

        activity = []
        for hour in range(24):
            hour_data = hourly_stats[hourly_stats["hour"] == hour]
            if not hour_data.empty:
                activity.append(
                    {
                        "hour": hour,
                        "avg_risk": float(hour_data["risk_score"].iloc[0]),
                        "total_volume": float(hour_data["amount"].iloc[0]),
                        "transaction_count": len(df[df["hour"] == hour]),
                    },
                )
            else:
                activity.append(
                    {
                        "hour": hour,
                        "avg_risk": 0.0,
                        "total_volume": 0.0,
                        "transaction_count": 0,
                    },
                )

        return activity

    def _analyze_network_patterns(self, df: Any) -> dict[str, Any]:
        """Analyze network patterns and connections."""
        _ensure_pandas()
        if df.empty:
            return {
                "total_connections": 0,
                "clusters": [],
                "centrality_metrics": {},
            }

        # Create address interaction matrix
        connections: dict[Any, set[Any]] = {}
        for _, row in df.iterrows():
            from_addr = row.get("from_addr")
            to_addr = row.get("to_addr")

            if from_addr and to_addr:
                if from_addr not in connections:
                    connections[from_addr] = set()
                connections[from_addr].add(to_addr)

        # Calculate basic network metrics
        vals = connections.values()
        total_connections = sum(len(targets) for targets in vals)

        # Find addresses with most connections (hubs)
        hub_addresses = sorted(
            connections.items(),
            key=lambda x: len(x[1]),
            reverse=True,
        )[:5]

        return {
            "total_connections": total_connections,
            "unique_senders": len(connections),
            "hub_addresses": [
                {"address": addr, "connection_count": len(targets)}
                for addr, targets in hub_addresses
            ],
            "avg_connections_per_address": (
                total_connections / len(connections) if connections else 0
            ),
        }

    def _calculate_anomaly_score(self, df: Any) -> float:
        """Calculate overall anomaly score for the dataset."""
        _ensure_pandas()
        _ensure_numpy()
        if df.empty or len(df) < 2:
            return 0.0

        # Calculate z - scores for amount anomalies
        # Ensure amounts is a float ndarray so numpy mean/std match typing
        amounts = np.asarray(df["amount"].astype(float).values)
        if len(amounts) > 1:
            mean = float(np.mean(amounts))
            std = float(np.std(amounts))
            if std > 0:
                z_scores = np.abs((amounts - mean) / std)
                anomaly_count = np.sum(z_scores > 2)
                return float(anomaly_count / len(amounts))

        return 0.0

    def _empty_metrics(self) -> AnalyticsMetrics:
        """Return empty metrics structure."""
        return AnalyticsMetrics(
            total_transactions=0,
            total_volume=0.0,
            avg_risk_score=0.0,
            high_risk_count=0,
            medium_risk_count=0,
            low_risk_count=0,
            unique_addresses=0,
            top_risk_addresses=[],
            risk_trend=[],
            category_distribution={},
            hourly_activity=[],
            network_analysis={},
            anomaly_score=0.0,
        )


class InsightsEngine:
    """AI - powered insights generator."""

    def generate_insights(self, metrics: AnalyticsMetrics):
        """Generate AI-powered insights from analytics data."""
        insights = []

        # Short locals to reduce long f-strings and keep line lengths down
        avg = metrics.avg_risk_score
        total = metrics.total_volume
        anomaly = metrics.anomaly_score
        network = metrics.network_analysis or {}

        # Risk level insights
        if avg > 0.7:
            insights.append(
                {
                    "type": "warning",
                    "title": "High Average Risk Detected",
                    "description": f"Avg risk {avg:.3f} elevated; review.",
                    "action": (
                        "Review high-risk transactions and consider "
                        "adjusting risk thresholds."
                    ),
                    "priority": "high",
                },
            )
        elif avg > 0.5:
            insights.append(
                {
                    "type": "info",
                    "title": "Moderate Risk Environment",
                    "description": f"Risk levels moderate at {avg:.3f}.",
                    "action": (
                        "Continue monitoring and prepare enhanced "
                        "due-diligence procedures."
                    ),
                    "priority": "medium",
                },
            )

        # Volume insights
        if total > 1000000:  # $1M threshold
            insights.append(
                {
                    "type": "info",
                    "title": "High Transaction Volume",
                    "description": f"Total volume ${total:,.2f}.",
                    "action": (
                        "Consider volume-based risk adjustments and "
                        "enhanced monitoring."
                    ),
                    "priority": "medium",
                },
            )

        # Anomaly insights
        if anomaly > 0.1:
            insights.append(
                {
                    "type": "warning",
                    "title": "Transaction Anomalies Detected",
                    "description": f"{anomaly:.1%} transactions anomalous.",
                    "action": ("Investigate unusual transaction amounts and patterns."),
                    "priority": "high",
                },
            )

        # Network insights
        if network.get("hub_addresses"):
            top_hub = network["hub_addresses"][0]
            if top_hub["connection_count"] > 10:
                insights.append(
                    {
                        "type": "info",
                        "title": "Network Hub Identified",
                        "description": (
                            f"Address {top_hub['address'][:10]}... has "
                            f"{top_hub['connection_count']} connections."
                        ),
                        "action": (
                            "Review hub address for potential money "
                            "laundering patterns."
                        ),
                        "priority": "medium",
                    },
                )

        return insights


# Global analytics instances: create lazily to avoid heavy import-time work


class _LazyProxy:
    """Simple lazy-initialization proxy for preserving public symbols.

    Instantiates the real object on first attribute access. This keeps the
    module API stable (callers can import `analytics_engine`) while avoiding
    eager construction during import.
    """

    def __init__(self, factory) -> None:
        self._factory = factory
        self._obj = None

    def _ensure(self) -> None:
        if self._obj is None:
            self._obj = self._factory()

    def __getattr__(self, name):
        self._ensure()
        return getattr(self._obj, name)

    def __call__(self, *args, **kwargs):
        self._ensure()
        # If the proxied object is callable, delegate the call. Otherwise,
        # raise a clear TypeError to match normal Python behavior.
        if callable(self._obj):
            return self._obj(*args, **kwargs)
        msg = f"'{type(self._obj).__name__}' object is not callable"
        raise TypeError(msg)


# Public lazy instances
analytics_engine = _LazyProxy(AdvancedAnalytics)
insights_engine = _LazyProxy(InsightsEngine)
