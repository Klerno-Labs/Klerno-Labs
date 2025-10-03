"""
AI Intelligence Module for Klerno Labs
Lightweight predictive analytics, anomaly detection, and recommendations
that work without heavy third-party ML dependencies.

Design:
- Uses lazy imports for pandas/numpy if available; otherwise, falls back to
  simple Python computations and safe defaults.
- Forecasting: simple exponential smoothing / moving average
- Anomaly detection: z-score / MAD-based detection
- Recommendations: heuristic rules based on risk and anomalies
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Dict, List

from . import store


def _try_import_numpy():
    if "np" in globals():
        return globals()["np"]
    try:
        import importlib

        np = importlib.import_module("numpy")
        globals()["np"] = np
        return np
    except Exception:
        return None


def _try_import_pandas():
    if "pd" in globals():
        return globals()["pd"]
    try:
        import importlib

        pd = importlib.import_module("pandas")
        globals()["pd"] = pd
        return pd
    except Exception:
        return None


@dataclass
class ForecastResult:
    horizon_days: int
    forecast: List[Dict[str, Any]]
    method: str


@dataclass
class AnomalyResult:
    method: str
    anomalies: List[Dict[str, Any]]
    summary: Dict[str, Any]


class IntelligenceEngine:
    """Lightweight analytics engine with forecasting and anomaly detection."""

    def __init__(self) -> None:
        self.alpha = 0.35  # smoothing factor
        self.min_points = 7

    def _load_transactions(self, days: int = 30) -> List[Dict[str, Any]]:
        rows = store.list_all(limit=50000)
        if not rows:
            return []
        # Filter by days window if timestamps present
        cutoff = datetime.now(UTC).replace(tzinfo=None)
        cutoff = cutoff.replace(microsecond=0)
        out: List[Dict[str, Any]] = []
        for r in rows:
            ts = r.get("timestamp")
            try:
                # accept str/iso as well
                if isinstance(ts, str):
                    # avoid heavy libs; parse minimally
                    # expected YYYY-MM-DD or ISO format
                    ts_obj = datetime.fromisoformat(ts.replace("Z", "+00:00")).replace(
                        tzinfo=None
                    )
                elif isinstance(ts, datetime):
                    ts_obj = ts.replace(tzinfo=None)
                else:
                    continue
            except Exception:
                continue
            r2 = dict(r)
            r2["timestamp"] = ts_obj
            out.append(r2)
        out.sort(key=lambda x: x["timestamp"])  # ascending
        return out[-days * 200 :]  # rough limit safeguard

    def _daily_series(
        self, rows: List[Dict[str, Any]], field: str = "amount"
    ) -> List[Dict[str, Any]]:
        if not rows:
            return []
        series: Dict[str, float] = {}
        for r in rows:
            d = r["timestamp"].date().isoformat()
            try:
                v = float(r.get(field, 0) or 0)
            except Exception:
                v = 0.0
            series[d] = series.get(d, 0.0) + v
        return [{"date": k, "value": v} for k, v in sorted(series.items())]

    def forecast_volume(self, days: int = 7) -> ForecastResult:
        """Simple exponential smoothing forecast for total daily volume."""
        rows = self._load_transactions(days=60)
        series = self._daily_series(rows, field="amount")
        if len(series) < self.min_points:
            return ForecastResult(days, [], method="naive")

        # initialize with moving average of first few points
        n_init = min(5, len(series))
        level = sum(pt["value"] for pt in series[:n_init]) / float(n_init)
        alpha = self.alpha
        for pt in series[n_init:]:
            level = alpha * float(pt["value"]) + (1 - alpha) * level

        # produce horizon forecasts (flat at last level)
        last_date = series[-1]["date"]
        try:
            last_dt = datetime.fromisoformat(last_date)
        except Exception:
            last_dt = datetime.now()
        fc = []
        for i in range(1, days + 1):
            d = (last_dt.date()).toordinal() + i
            dt = datetime.fromordinal(d)
            fc.append(
                {"date": dt.date().isoformat(), "predicted_volume": round(level, 2)}
            )
        return ForecastResult(days, fc, method="exp_smoothing")

    def detect_anomalies(self) -> AnomalyResult:
        """Z-score anomaly detection on daily volumes."""
        rows = self._load_transactions(days=60)
        series = self._daily_series(rows, field="amount")
        if len(series) < self.min_points:
            return AnomalyResult(method="zscore", anomalies=[], summary={"count": 0})

        values = [float(pt["value"]) for pt in series]
        mean = sum(values) / len(values)
        # population std safeguard
        var = sum((v - mean) ** 2 for v in values) / max(1, len(values))
        std = (var**0.5) if var > 0 else 0.0
        anomalies: List[Dict[str, Any]] = []
        threshold = 3.0
        for pt, v in zip(series, values):
            z = (v - mean) / std if std > 0 else 0.0
            if abs(z) >= threshold:
                anomalies.append(
                    {"date": pt["date"], "value": v, "zscore": round(z, 2)}
                )

        return AnomalyResult(
            method="zscore",
            anomalies=anomalies,
            summary={
                "count": len(anomalies),
                "mean": round(mean, 2),
                "std": round(std, 2),
                "threshold": threshold,
            },
        )

    def recommendations(self) -> List[Dict[str, Any]]:
        """Heuristic recommendations based on anomalies and recent risk levels."""
        rows = self._load_transactions(days=14)
        if not rows:
            return []
        # recent risk average
        risks: List[float] = []
        for r in rows[-300:]:
            try:
                risks.append(float(r.get("risk_score") or r.get("score") or 0.0))
            except Exception:
                continue
        avg_risk = (sum(risks) / len(risks)) if risks else 0.0
        anoms = self.detect_anomalies()
        items: List[Dict[str, Any]] = []
        if anoms.summary.get("count", 0) >= 2 and avg_risk >= 0.5:
            items.append(
                {
                    "type": "investigate",
                    "title": "Elevated volume anomalies with higher risk",
                    "action": "Drill into top-risk addresses and recent spikes",
                    "priority": "high",
                }
            )
        elif avg_risk >= 0.7:
            items.append(
                {
                    "type": "mitigate",
                    "title": "High average risk detected",
                    "action": "Tighten transaction thresholds and enable MFA challenges",
                    "priority": "high",
                }
            )
        else:
            items.append(
                {
                    "type": "monitor",
                    "title": "System healthy",
                    "action": "Continue monitoring; no action required",
                    "priority": "low",
                }
            )
        return items

    def insights(self, horizon_days: int = 7) -> Dict[str, Any]:
        fc = self.forecast_volume(horizon_days)
        an = self.detect_anomalies()
        recs = self.recommendations()
        return {
            "forecast": {
                "method": fc.method,
                "horizon_days": fc.horizon_days,
                "points": fc.forecast,
            },
            "anomalies": {
                "method": an.method,
                "summary": an.summary,
                "items": an.anomalies,
            },
            "recommendations": recs,
        }
