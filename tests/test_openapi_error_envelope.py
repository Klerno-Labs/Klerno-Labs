from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from app.main import app


def test_openapi_has_error_envelope_and_examples() -> None:
    client = TestClient(app)
    r = client.get("/openapi.json")
    assert r.status_code == 200
    data: dict[str, Any] = r.json()

    # ErrorEnvelope schema exists
    comps = data.get("components", {})
    schemas = comps.get("schemas", {})
    assert "ErrorEnvelope" in schemas

    # At least one operation has a default error response referencing ErrorEnvelope with example
    found = False
    paths = data.get("paths", {})
    for _p, item in paths.items():
        for method, op in item.items():
            if method.lower() not in {
                "get",
                "post",
                "put",
                "patch",
                "delete",
                "options",
                "head",
            }:
                continue
            responses = op.get("responses", {})
            for code, meta in responses.items():
                if code in {"400", "401", "403", "404", "422", "429", "500"}:
                    content = meta.get("content", {}).get("application/json", {})
                    schema = content.get("schema", {})
                    if schema.get("$ref") == "#/components/schemas/ErrorEnvelope":
                        # Example present and has 'error' object
                        ex = content.get("example")
                        if isinstance(ex, dict) and isinstance(ex.get("error"), dict):
                            found = True
                            break
            if found:
                break
        if found:
            break

    assert found, "No default error response with ErrorEnvelope example found"
