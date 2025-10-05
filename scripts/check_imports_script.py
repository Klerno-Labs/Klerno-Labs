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
    except Exception:
        traceback.print_exc()
