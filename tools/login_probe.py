import argparse
import json
import time
from datetime import UTC, datetime
from pathlib import Path

import requests

try:
    import keyring
except Exception:
    keyring = None

import base64


def save_tokens(dest: Path, tokens: dict) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("w", encoding="utf8") as f:
        json.dump(tokens, f, indent=2)


def _parse_jwt_exp(jwt_token: str) -> int | None:
    # Very small, dependency-free JWT exp parser: split, base64-decode payload,
    # extract 'exp' as int if present. Returns epoch seconds or None.
    try:
        parts = jwt_token.split(".")
        if len(parts) < 2:
            return None
        payload_b64 = parts[1]
        # Fix padding
        padding = "=" * (-len(payload_b64) % 4)
        payload_b64 += padding
        data = base64.urlsafe_b64decode(payload_b64.encode("ascii"))
        obj = json.loads(data)
        exp = obj.get("exp")
        if isinstance(exp, (int, float)):
            return int(exp)
    except Exception:
        return None
    return None


def main(save_token: bool = False, use_keyring: bool = False) -> int:
    """Probe multiple common local ports and login endpoints to find a running dev server.

    Tries JSON first then form-encoded payload if JSON fails. Prints the first successful
    response and optionally saves tokens to `.run/dev_tokens.json`.
    """

    ports = [8000, 9000, 9001]
    paths = ["/auth/login_api", "/auth/login", "/auth/login/api"]
    payload = {"email": "dev@example.com", "password": "anything"}

    print("Probing local ports for login endpoints...\n")
    for port in ports:
        for path in paths:
            url = f"http://127.0.0.1:{port}{path}"
            try:
                r = requests.post(url, json=payload, timeout=2)
            except Exception as e_json:
                # Try form-encoded body as a fallback
                try:
                    r = requests.post(url, data=payload, timeout=2)
                except Exception as e_form:
                    print(
                        f"{url} -> connection error (json:{e_json!r} / form:{e_form!r})"
                    )
                    continue

            print(f"{url} -> {r.status_code}")
            try:
                body = r.json()
                print("json:", body)
            except Exception:
                body = None
                print("text:", (r.text or "")[:1000])

            if r.status_code == 200:
                print("[SUCCESS] login succeeded at", url)
                if save_token and body:
                    tokens = {
                        k: body.get(k)
                        for k in ("access_token", "refresh_token")
                        if body.get(k)
                    }
                    if tokens:
                        saved = {
                            "url": url,
                            "user": payload["email"],
                            "saved_at": datetime.now(UTC).isoformat(),
                            "tokens": tokens,
                        }
                        # try parse expiry from access token
                        at = tokens.get("access_token")
                        if at:
                            exp_ts = _parse_jwt_exp(at)
                            if exp_ts:
                                saved["access_token_expiry"] = datetime.fromtimestamp(
                                    exp_ts, tz=UTC
                                ).isoformat()

                        if use_keyring and keyring:
                            try:
                                keyring.set_password(
                                    "klerno.dev.tokens",
                                    payload["email"],
                                    json.dumps(saved),
                                )
                                print(
                                    "Saved tokens to OS keyring (service=klerno.dev.tokens)"
                                )
                                return 0
                            except Exception as e:
                                print("keyring save failed, falling back to file:", e)

                        dest = Path(".run") / "dev_tokens.json"
                        save_tokens(dest, saved)
                        print(f"Saved tokens to {dest}")
                return 0
            # small delay to avoid spamming
            time.sleep(0.05)

    print("No successful login found on probed ports/paths")
    return 1


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument(
        "--save-token",
        action="store_true",
        help="Save access/refresh tokens to .run/dev_tokens.json",
    )
    p.add_argument(
        "--use-keyring",
        action="store_true",
        help="Store tokens in the OS keyring instead of a file (if available)",
    )
    args = p.parse_args()
    raise SystemExit(main(save_token=args.save_token, use_keyring=args.use_keyring))
