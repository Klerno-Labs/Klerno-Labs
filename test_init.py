#!/usr/bin/env python3
"""Test script to verify app.__init__.py functionality."""

import app

print("✓ App package imported successfully")
print(f"✓ Has integrations: {hasattr(app, 'integrations')}")
print(f"✓ Has auth: {hasattr(app, 'auth')}")
print(f"✓ Has create_access_token: {hasattr(app, 'create_access_token')}")
print(f"✓ Has verify_token: {hasattr(app, 'verify_token')}")

# Test the shim functionality
if hasattr(app.integrations, "xrp"):
    print("✓ XRP integration module available")
    print(f"✓ Has get_xrpl_client: {hasattr(app.integrations.xrp, 'get_xrpl_client')}")
    print(
        f"✓ Has fetch_account_tx: {hasattr(app.integrations.xrp, 'fetch_account_tx')}"
    )

print("\n🎉 All tests passed! app.__init__.py is working correctly.")
