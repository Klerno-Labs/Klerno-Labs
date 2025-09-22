from fastapi.testclient import TestClient

from app.main import app
from app.security import expected_api_key

client = TestClient(app)


def _headers():
    key = (expected_api_key() or "").strip()
    return {"X-API-Key": key} if key else {}


def test_build_message_endpoint_pain001():
    payload = {
        "message_type": "pain.001",
        "data": {
            "message_id": "T-EP-1",
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
    r = client.post(
        "/enterprise/iso20022/build-message", json=payload, headers=_headers()
    )
    assert r.status_code == 200
    j = r.json()
    assert j.get("status") == "success"
    assert "pain.001" in j.get("message_type", "")
    assert len(j.get("xml", "")) > 0


def test_validate_xml_endpoint_pain001():
    # Build XML via endpoint, then post to validate-xml
    payload = {
        "message_type": "pain.001",
        "data": {
            "message_id": "T-EP-2",
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
    r1 = client.post(
        "/enterprise/iso20022/build-message", json=payload, headers=_headers()
    )
    assert r1.status_code == 200
    xml = r1.json().get("xml", "").encode("utf-8")

    r2 = client.post(
        "/enterprise/iso20022/validate-xml", content=xml, headers=_headers()
    )
    assert r2.status_code == 200
    j2 = r2.json()
    assert j2.get("status") == "success"
    assert j2.get("validation_result", {}).get("valid") is True
