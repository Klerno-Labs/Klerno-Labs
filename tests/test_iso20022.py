from datetime import UTC, datetime

from app.iso20022_compliance import (
    CurrencyCode,
    ISO20022Amount,
    ISO20022Manager,
    ISO20022MessageBuilder,
    ISO20022Parser,
    ISO20022PartyIdentification,
    ISO20022PaymentInstruction,
    PaymentPurpose,
)


def test_build_and_parse_pain001_roundtrip():
    builder = ISO20022MessageBuilder()
    parser = ISO20022Parser()

    debtor = ISO20022PartyIdentification(name="Alice")
    creditor = ISO20022PartyIdentification(name="Bob")
    instr = ISO20022PaymentInstruction(
        instruction_id="INSTR - 1",
        end_to_end_id="E2E - 1",
        amount=ISO20022Amount(currency=CurrencyCode.USD, value="10.50"),
        debtor=debtor,
        creditor=creditor,
        debtor_account="DE89370400440532013000",
        creditor_account="GB29NWBK60161331926819",
        payment_purpose=PaymentPurpose.COMC,
        execution_date=datetime.now(UTC),
    )

    xml = builder.create_pain001_message(
        message_id="MSG - 1",
        creation_datetime=datetime.now(UTC),
        initiating_party=ISO20022PartyIdentification(name="Klerno"),
        payment_instructions=[instr],
    )

    assert "<Document" in xml
    parsed = parser.parse_pain001(xml)
    assert parsed["message_type"] == "pain.001"
    assert parsed["group_header"]["message_id"] == "MSG - 1"
    assert parsed["payment_instructions"][0]["instruction_id"] == "INSTR - 1"


def test_manager_validate_dict_and_xml():
    mgr = ISO20022Manager()

    # dict validation
    dict_payload = {
        "instruction_id": "INSTR - 1",
        "end_to_end_id": "E2E - 1",
        "amount": {"value": "100.00", "currency": "EUR"},
        "debtor": {"name": "Alice"},
        "creditor": {"name": "Bob"},
        "debtor_account": "DE89370400440532013000",
        "creditor_account": "GB29NWBK60161331926819",
        "payment_purpose": "OTHR",
    }
    vr = mgr.validate_message(dict_payload)
    assert vr["valid"] is True

    # xml validation
    msg_type = (
        mgr.message_builder.PAIN_001
        if hasattr(mgr.message_builder, "PAIN_001")
        else None
    )
    xml = mgr.create_payment_instruction(
        message_type=msg_type,
        payment_data={
            "message_id": "MSG - XML",
            "creation_datetime": datetime.now(UTC),
            "initiating_party": {"name": "Klerno"},
            "payment_instructions": [dict_payload],
        },
    )
    vr2 = mgr.validate_message(xml)
    assert vr2["valid"] is True


def test_validator_amount_precision():
    from app.iso20022_compliance import iso20022_validator

    assert iso20022_validator.validate_amount("1.123456789012345678")
    assert not iso20022_validator.validate_amount("1.1234567890123456789")
