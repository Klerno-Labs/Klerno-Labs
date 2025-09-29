"""Diagnostic helper: prints structlog inner logger types and lists FastAPI app routes.

Run inside the project's Python environment (venv) to avoid PowerShell quoting issues.
"""

import sys
from importlib import import_module

# Ensure project root on path
sys.path.insert(0, ".")

# Import logging config and try to configure
try:
    import app.logging_config as lc

    lc.configure_logging()
    print("configured logging via app.logging_config.configure_logging()")
except Exception as e:
    print("failed to configure logging:", e)

# Inspect structlog get_logger
try:
    import structlog

    lg = structlog.get_logger("diagnostic")
    print("structlog.get_logger() ->", type(lg))
    try:
        inner = getattr(lg, "_logger", None)
        print("-> inner logger:", type(inner), repr(inner))
    except Exception as e:
        print("-> error accessing inner:", e)
except Exception as e:
    print("structlog import error:", e)

# Import the FastAPI app and list routes
try:
    # Import main app module - try both app.main and app.__init__ pathways
    app_mod = None
    for name in ("app.main", "app"):
        try:
            app_mod = import_module(name)
            print(f"imported {name} successfully")
            break
        except Exception as e:
            print(f"import {name} failed:", e)

    if app_mod is None:
        print("could not import app module")
        sys.exit(1)

    # Try to find FastAPI app object
    maybe_app = getattr(app_mod, "app", None) or getattr(app_mod, "create_app", None)
    if maybe_app is None:
        # try other common places
        attrs = [a for a in dir(app_mod) if a.lower().endswith("app")]
        for a in attrs:
            val = getattr(app_mod, a)
            if getattr(val, "routes", None) is not None:
                maybe_app = val
                break

    if maybe_app is None:
        print("could not find FastAPI app object in module", app_mod)
    else:
        print("Found app object:", maybe_app)
        routes = []
        for r in maybe_app.routes:
            routes.append(
                (getattr(r, "path", None), getattr(r, "methods", None), type(r))
            )
        print(f"Registered routes (count={len(routes)}):")
        for p, m, t in routes:
            print(" -", p, m, t)

except Exception as e:
    print("error inspecting app routes:", e)

print("\nDone")


def main() -> int:
    """Run diagnostic and capture output into .run/diagnostic-startup.txt for CI artifacts.

    Returns 0 on success, 1 on import/app-not-found, 2 on other exceptions.
    """
    import io
    import traceback

    out = io.StringIO()
    try:
        # Re-run the module-level logic but capture stdout/stderr into the buffer.
        # For simplicity, execute this file's global code path by calling the functions above
        # — the module already ran at import; here we just replay essential checks.
        out.write("\n--- Diagnostic replay ---\n")
        try:
            from importlib import import_module as _import_module

            _import_module("structlog")
            out.write("structlog available\n")
        except Exception as e:
            out.write(f"structlog import error: {e}\n")

        try:
            from importlib import import_module as _import_module

            app_mod = None
            for name in ("app.main", "app"):
                try:
                    app_mod = _import_module(name)
                    out.write(f"imported {name} successfully\n")
                    break
                except Exception as e:
                    out.write(f"import {name} failed: {e}\n")

            if app_mod is None:
                out.write("could not import app module\n")
                code = 1
            else:
                maybe_app = getattr(app_mod, "app", None) or getattr(
                    app_mod, "create_app", None
                )
                if maybe_app is None:
                    attrs = [a for a in dir(app_mod) if a.lower().endswith("app")]
                    for a in attrs:
                        val = getattr(app_mod, a)
                        if getattr(val, "routes", None) is not None:
                            maybe_app = val
                            break

                if maybe_app is None:
                    out.write(
                        "could not find FastAPI app object in module "
                        + repr(app_mod)
                        + "\n"
                    )
                    code = 1
                else:
                    out.write(f"Found app object: {maybe_app}\n")
                    code = 0
        except Exception:
            out.write("error inspecting app routes:\n")
            out.write(traceback.format_exc())
            code = 2

    except Exception:
        out.write("diagnostic main failed:\n")
        out.write(traceback.format_exc())
        code = 2

    # Ensure output dir
    import os

    os.makedirs(".run", exist_ok=True)
    path = os.path.join(".run", "diagnostic-startup.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(out.getvalue())

    print(f"Wrote diagnostic output to {path}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
