from fastapi.testclient import TestClient

from app.main import app

ALLOWED = {200, 201, 202, 204, 301, 302, 303, 307, 308, 401, 403, 405, 422}

# Known environment-dependent or synthetic routes to skip in generic smoke
SKIP_EXACT = {
    "/api/neon/notes",
    "/api/neon/paragraphs",
    "/analytics/dashboard",
    "/integrations/xrpl/fetch",
}
SKIP_PREFIX = (
    "/ws",
    "/static/",
    "/analytics/",  # dashboard aggregates dynamic data that may not be stable in smoke
    "/admin/analytics/",
    "/integrations/",
)


def test_all_get_routes_do_not_500() -> None:
    # Don't raise exceptions: collect 500s as responses so we can report them
    client = TestClient(app, raise_server_exceptions=False)
    errors: list[tuple[str, int]] = []

    for route in app.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", set())
        if not path or "GET" not in methods:
            continue
        # Skip parametric and environment-dependent paths
        if path in SKIP_EXACT or any(path.startswith(p) for p in SKIP_PREFIX):
            continue
        if "{" in path:
            continue

        r = client.get(path)
        if r.status_code >= 500:
            errors.append((path, r.status_code))
        elif r.status_code not in ALLOWED:
            errors.append((path, r.status_code))

    assert not errors, f"GET route issues: {errors}"
