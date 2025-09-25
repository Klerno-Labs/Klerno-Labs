import time

import requests

base = "http://127.0.0.1:8000"


def wait_for(url, timeout: int = 15) -> bool:
    start = time.time()
    while time.time() - start < timeout:
        try:
            requests.get(url, timeout=2)
            return True
        except Exception:
            time.sleep(0.5)
    return False


if not wait_for(base + "/health", timeout=15):
    print("Server not responding at", base)
    raise SystemExit(1)

print("GET /")
r = requests.get(base + "/")
print(r.status_code, "len=", len(r.text))

print("GET /auth/login")
r = requests.get(base + "/auth/login")
print(r.status_code, "len=", len(r.text))

print("POST /auth/login (form)")
resp = requests.post(
    base + "/auth/login",
    data={
        "email": "klerno@outlook.com",
        "password": "Labs2025",
    },
    allow_redirects=False,
)
print("status", resp.status_code)
print("headers:", dict(resp.headers))
print("cookies:", resp.cookies.get_dict())
print("location:", resp.headers.get("location"))

# If login returned Set-Cookie, try /dashboard
if resp.cookies.get("session"):
    s = requests.Session()
    s.cookies.update(resp.cookies.get_dict())
    r2 = s.get(base + "/dashboard")
    print("/dashboard status", r2.status_code)
else:
    print("No session cookie received; login likely failed")
