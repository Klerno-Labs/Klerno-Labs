import traceback

modules = [
    "app.main",
    "app.settings",
    "app.auth",
    "app.admin",
    "app.enterprise_security_enhanced",
    "app.transactions",
]

for m in modules:
    try:
        __import__(m)
        print(f"OK: {m}")
    except Exception:
        print(f"ERROR importing {m}")
        traceback.print_exc()
