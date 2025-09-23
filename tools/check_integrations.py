import importlib

importlib.invalidate_caches()
import app

print("app.integrations repr ->", repr(getattr(app, "integrations", None)))
print("type ->", type(getattr(app, "integrations", None)))
print("has xrp ->", hasattr(getattr(app, "integrations", None), "xrp"))
try:
    import integrations as top

    print("top-level integrations __all__ ->", getattr(top, "__all__", None))
    print("top-level xrp attr ->", getattr(top, "xrp", None))
except Exception as e:
    print("failed to import top-level integrations ->", e)
