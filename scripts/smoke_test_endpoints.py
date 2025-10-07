import asyncio
import os
import sys
from pathlib import Path

import httpx

# In-process ASGI smoke test hitting key routes


async def run_smoke():
    # Ensure workspace root is on sys.path so 'app' can be imported when run from any CWD
    script_dir = Path(__file__).resolve().parent
    workspace_root = (script_dir / os.pardir).resolve()
    if str(workspace_root) not in sys.path:
        sys.path.insert(0, str(workspace_root))

    # Ensure Neon proxy has a base URL; token optional for these checks
    os.environ.setdefault(
        "VITE_NEON_DATA_API_URL",
        "https://ep-odd-wave-adbr94n5.apirest.c-2.us-east-1.aws.neon.tech/neondb/rest/v1",
    )
    os.environ.setdefault("NEON_API_KEY", "dummy")
    # Import app in prod-like mode
    from app.main import app as fastapi_app

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=fastapi_app),  # type: ignore[arg-type]
        base_url="http://testserver",
    ) as client:
        paths = [
            ("/", (200,)),
            ("/health", (200,)),
            ("/docs", (200,)),
            # For Neon proxy, any non-404 response counts as reachable; 401 is expected without a real JWT
            ("/api/neon/notes", tuple(code for code in range(100, 600) if code != 404)),
        ]
        posts: list[tuple[str, dict]] = [
            ("/analyze/sample", {}),
            ("/iso20022/parse", {"xml": "<Message/>"}),
            ("/iso20022/analyze-compliance", {"xml": "<Message/>"}),
            (
                "/enterprise/iso20022/build-message",
                {"message_type": "pacs.008"},
            ),
            ("/enterprise/iso20022/validate-xml", {}),
        ]
        results: list[tuple[str, int | str]] = []
        for path, _ok_codes in paths:
            try:
                r = await client.get(path)
                results.append((path, r.status_code))
            except Exception as e:
                results.append((path, f"unreachable: {e.__class__.__name__}"))
        for path, payload in posts:
            try:
                r = await client.post(path, json=payload)
                results.append((path, r.status_code))
            except Exception as e:
                results.append((path, f"unreachable: {e.__class__.__name__}"))
        return results


if __name__ == "__main__":
    # Retry a couple of times to avoid transient flakiness
    attempts = 2
    for attempt in range(1, attempts + 1):
        out = asyncio.run(run_smoke())
        print(f"Attempt {attempt}:")
        bad = False
        for path, code in out:
            print(f"  {path} -> {code}")
            if code == 404 or (
                isinstance(code, str) and code.startswith("unreachable")
            ):
                bad = True
        if not bad:
            break
        asyncio.run(asyncio.sleep(0.5))
