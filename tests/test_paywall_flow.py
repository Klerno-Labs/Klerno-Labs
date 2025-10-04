def test_landing_and_paywall_redirect(test_client):
    """Smoke test: landing page renders and paywall redirect logic.

    Lightweight: no real users or payments. Verifies templates and redirect
    behavior for the paywall endpoints.
    """
    # Landing page should be available
    r = test_client.get("/")
    assert r.status_code == 200
    assert "Klerno Labs" in r.text

    # Visit paywall page
    r = test_client.get("/paywall")
    assert r.status_code == 200

    # Submitting wrong code should redirect back with err=1
    r = test_client.post(
        "/paywall/verify", data={"code": "wrongcode"}, follow_redirects=False,
    )
    assert r.status_code in (302, 303)
    assert "/paywall?err=1" in r.headers.get("location", "")

    # Submitting the correct code (default PAYWALL_CODE) should redirect to
    # the dashboard. Use the environment default; server will set a cookie on
    # success.
    from app.paywall import PAYWALL_CODE

    r = test_client.post(
        "/paywall/verify", data={"code": PAYWALL_CODE}, follow_redirects=False,
    )
    assert r.status_code in (302, 303)
    loc = r.headers.get("location", "")
    assert "/dashboard" in loc or "/dashboard?key=" in loc
