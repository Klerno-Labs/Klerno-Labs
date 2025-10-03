from fastapi.testclient import TestClient

from app.main import app


def test_ai_insights_endpoint_smoke():
    client = TestClient(app)
    r = client.get("/ai/insights?horizon_days=3")
    assert r.status_code == 200
    data = r.json()
    assert "forecast" in data
    assert "anomalies" in data
    assert "recommendations" in data
    # structure checks (lenient)
    assert isinstance(data["forecast"].get("horizon_days"), int)
    assert isinstance(data["anomalies"].get("summary"), dict)
