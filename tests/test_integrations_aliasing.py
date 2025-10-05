from __future__ import annotations

from unittest.mock import patch


def test_app_integrations_xrp_aliasing_importable() -> None:
    # Importing should succeed via the aliased path
    import app

    # Access attribute to ensure it's present
    assert hasattr(app.integrations, "xrp"), "app.integrations.xrp should be available"


def test_app_integrations_xrp_patch_path_resolves() -> None:
    # Able to patch a symbol on the XRPL module via app.integrations path
    with patch("app.integrations.xrp.get_xrpl_client") as mocked:
        # Referencing the patched function should work without ImportError/AttributeError
        import integrations.xrp as real_xrp

        # Call through to ensure patch was applied to the shared module object
        try:
            real_xrp.get_xrpl_client()
        except Exception:
            # We don't care about runtime behavior, just that the symbol is resolvable and callable
            pass
        assert mocked.called is True
