"""FastAPI endpoints exposing AI intelligence features."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from .intelligence import IntelligenceEngine

router = APIRouter(prefix="/ai", tags=["ai"])
engine = IntelligenceEngine()


@router.get("/insights")
def get_insights(horizon_days: int = 7) -> Any:
    return engine.insights(horizon_days=horizon_days)


@router.get("/forecast")
def get_forecast(horizon_days: int = 7) -> Any:
    return engine.forecast_volume(days=horizon_days).__dict__


@router.get("/anomalies")
def get_anomalies() -> Any:
    r = engine.detect_anomalies()
    return {"method": r.method, "summary": r.summary, "items": r.anomalies}
