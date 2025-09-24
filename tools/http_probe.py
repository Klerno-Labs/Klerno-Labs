import urllib.request
from urllib.error import HTTPError, URLError

BASE = "http://127.0.0.1:8002"
paths = [
    "/",
    "/signup",
    "/login",
    "/auth/login",
    "/auth/signup",
    "/admin/",
    "/static/js/main.js",
    "/js/main.js",
    "/static/images/hero-bg.jpg",
    "/images/hero-bg.jpg",
    "/offline.html",
]


def probe(path):
    url = BASE + path
    req = urllib.request.Request(url, headers={"User-Agent": "probe/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, resp.getheader("Content-Type")
    except HTTPError as e:
        return e.code, e.headers.get("Content-Type")
    except URLError as e:
        return None, str(e.reason)


if __name__ == "__main__":
    for p in paths:
        status, ctype = probe(p)
        print(f"{p}: {status} - {ctype}")
