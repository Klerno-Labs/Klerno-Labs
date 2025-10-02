import requests

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


def probe(path, timeout: int = 5):
    url = BASE + path
    headers = {"User-Agent": "probe/1.0"}
    try:
        resp = requests.get(url, headers=headers, timeout=timeout)
        return resp.status_code, resp.headers.get("Content-Type")
    except requests.exceptions.HTTPError as e:
        return e.response.status_code if e.response is not None else None, None
    except requests.exceptions.RequestException as e:
        return None, str(e)


if __name__ == "__main__":
    for p in paths:
        status, ctype = probe(p)
        print(f"{p}: {status} - {ctype}")
