import os
import sys
from fastapi.testclient import TestClient

# Ensure repository root is on sys.path when running as a script
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from app.main import app
from app.security import expected_api_key


def _headers():
    key = (expected_api_key() or "").strip()
    return {"X-API-Key": key} if key else {}


def main() -> int:
    client = TestClient(app)

    # 1) Status
    r = client.get("/enterprise/iso20022/status", headers=_headers())
    if r.status_code != 200:
        print(f"status endpoint failed: {r.status_code}")
        return 1
    js = r.json()
    if not (js.get("status") == "success" and isinstance(js.get("compliance_report"), dict)):
        print(f"unexpected status payload: {js}")
        return 1

    # 2) Cryptos
    r = client.get("/enterprise/iso20022/cryptos", headers=_headers())
    if r.status_code != 200:
        print(f"cryptos endpoint failed: {r.status_code}")
        return 1
    js = r.json()
    data = js.get("data")
    if not (js.get("status") == "success" and isinstance(data, dict) and len(data) > 0):
        print(f"unexpected cryptos payload: {js}")
        return 1

    # 3) Build pain.001
    payload = {
        "message_type": "pain.001",
        "data": {
            "message_id": "CI-SMOKE-1",
            "creation_datetime": "2025-01-01T00:00:00Z",
            "initiating_party": {"name": "Klerno"},
            "payment_instructions": [
                {
                    "instruction_id": "I1",
                    "end_to_end_id": "E1",
                    "amount": {"value": "5.00", "currency": "USD"},
                    "debtor": {"name": "Alice"},
                    "creditor": {"name": "Bob"},
                    "debtor_account": "DE89370400440532013000",
                    "creditor_account": "GB29NWBK60161331926819",
                }
            ],
        },
    }
    r = client.post("/enterprise/iso20022/build-message", json=payload, headers=_headers())
    if r.status_code != 200:
        print(f"build-message failed: {r.status_code} {r.text}")
        return 1
    js = r.json()
    if not (js.get("status") == "success" and "pain.001" in js.get("message_type", "") and len(js.get("xml", "")) > 0):
        print(f"unexpected build-message payload: {js}")
        return 1

    xml = js.get("xml", "").encode("utf-8")

    # 4) Validate XML
    r = client.post("/enterprise/iso20022/validate-xml", content=xml, headers=_headers())
    if r.status_code != 200:
        print(f"validate-xml failed: {r.status_code} {r.text}")
        return 1
    js = r.json()
    if not (js.get("status") == "success" and js.get("validation_result", {}).get("valid") is True):
        print(f"unexpected validate-xml payload: {js}")
        return 1

    print("CI ISO endpoint smoke: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
