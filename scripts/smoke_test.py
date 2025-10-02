import time

import requests

BASE = "http://127.0.0.1:8000"
DEFAULT_TIMEOUT = 5


def wait_for(url: str, timeout: int = 15) -> bool:
    """Wait for the given URL to respond within timeout seconds.

    Uses DEFAULT_TIMEOUT for individual requests to ensure Bandit does not
    complain about requests without timeouts.
    """
    start = time.time()
    while time.time() - start < timeout:
        try:
            requests.get(url, timeout=DEFAULT_TIMEOUT)
            return True
        except Exception:
            time.sleep(0.5)
    return False


if not wait_for(BASE + "/health", timeout=15):
    print("Server not responding at", BASE)
    raise SystemExit(1)

print("GET /")
r = requests.get(BASE + "/", timeout=DEFAULT_TIMEOUT)
print(r.status_code, "len=", len(r.text))

print("GET /auth/login")
r = requests.get(BASE + "/auth/login", timeout=DEFAULT_TIMEOUT)
print(r.status_code, "len=", len(r.text))

print("POST /auth/login (form)")
resp = requests.post(
    BASE + "/auth/login",
    data={
        "email": "klerno@outlook.com",
        "password": "Labs2025",
    },
    allow_redirects=False,
    timeout=DEFAULT_TIMEOUT,
)
print("status", resp.status_code)
print("headers:", dict(resp.headers))
print("cookies:", resp.cookies.get_dict())
print("location:", resp.headers.get("location"))

# If login returned Set-Cookie, try /dashboard
if resp.cookies.get("session"):
    s = requests.Session()
    s.cookies.update(resp.cookies.get_dict())
    r2 = s.get(BASE + "/dashboard", timeout=DEFAULT_TIMEOUT)
    print("/dashboard status", r2.status_code)
else:
    print("No session cookie received; login likely failed")
