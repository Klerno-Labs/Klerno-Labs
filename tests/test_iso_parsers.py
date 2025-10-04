from datetime import UTC, datetime

from app.iso20022_compliance import (
    CurrencyCode,
    ISO20022Amount,
    ISO20022MessageBuilder,
    ISO20022Parser,
    ISO20022PartyIdentification,
    ISO20022PaymentInstruction,
    PaymentPurpose,
)


def _build_sample_pain001_xml():
    b = ISO20022MessageBuilder()
    instr = ISO20022PaymentInstruction(
        instruction_id="I1",
        end_to_end_id="E1",
        amount=ISO20022Amount(currency=CurrencyCode.USD, value="1.00"),
        debtor=ISO20022PartyIdentification(name="A"),
        creditor=ISO20022PartyIdentification(name="B"),
        debtor_account="DE89370400440532013000",
        creditor_account="GB29NWBK60161331926819",
        payment_purpose=PaymentPurpose.OTHR,
        execution_date=datetime.now(UTC),
    )
    return b.create_pain001_message(
        "M1", datetime.now(UTC), ISO20022PartyIdentification(name="K"), [instr],
    )


def test_parse_pain002_minimal():
    # Minimal synthetic pain.002 - like structure using builder namespace
    xml = """
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pain.002.001.12">
 <PmtStsRpt>
 <GrpHdr>
 <MsgId > MSG2</MsgId>
 <CreDtTm > 2025 - 01 - 01T00:00:00Z</CreDtTm>
 </GrpHdr>
 <OrgnlGrpInfAndSts>
 <OrgnlMsgId > MSG1</OrgnlMsgId>
 <OrgnlMsgNmId > pain.001.001.11</OrgnlMsgNmId>
 </OrgnlGrpInfAndSts>
 <TxInfAndSts>
 <StsId > STS1</StsId>
 <OrgnlInstrId > I1</OrgnlInstrId>
 <TxSts > ACSC</TxSts>
 <StsRsnInf>
 <Rsn>
 <Cd > ACSC</Cd>
 </Rsn>
 <AddtlInf > Processed</AddtlInf>
 </StsRsnInf>
 <AddtlInf > ok</AddtlInf>
 </TxInfAndSts>
 </PmtStsRpt>
</Document>
""".strip()
    p = ISO20022Parser()
    out = p.parse_pain002(xml)
    assert out["message_type"] == "pain.002"
    assert out["group_header"]["message_id"] == "MSG2"
    assert out["original_message"]["original_message_id"] == "MSG1"
    assert out["transactions"][0]["status"] == "ACSC"
    assert out["transactions"][0]["reasons"]["code"] == "ACSC"
    assert "Processed" in out["transactions"][0]["reasons"]["additional_info"]


def test_parse_camt053_minimal():
    xml = """
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.10">
 <BkToCstmrStmt>
 <GrpHdr>
 <MsgId > MSGS</MsgId>
 <CreDtTm > 2025 - 01 - 01T00:00:00Z</CreDtTm>
 </GrpHdr>
 <Stmt>
 <Id > STMT - 1</Id>
 <Acct><Id><IBAN > DE00TEST</IBAN></Id></Acct>
 <Bal>
 <Tp>
 <CdOrPrtry><Cd > CLBD</Cd></CdOrPrtry>
 </Tp>
 <Amt Ccy="USD">100.00</Amt>
 <Dt > 2025 - 01 - 02</Dt>
 </Bal>
 <Ntry>
 <NtryRef > R1</NtryRef>
 <CdtDbtInd > CRDT</CdtDbtInd>
 <Amt Ccy="USD">10.00</Amt>
 <BookgDt><Dt > 2025 - 01 - 02</Dt></BookgDt>
 <ValDt><Dt > 2025 - 01 - 02</Dt></ValDt>
 </Ntry>
 </Stmt>
 </BkToCstmrStmt>
</Document>
""".strip()
    p = ISO20022Parser()
    out = p.parse_camt053(xml)
    assert out["message_type"] == "camt.053"
    assert out["group_header"]["message_id"] == "MSGS"
    assert out["statement"]["id"] == "STMT - 1"
    assert out["statement"]["transactions"][0]["amount"] == "10.00"
    # Balance parsed
    assert out["statement"]["balances"][0]["type"] == "CLBD"
    assert out["statement"]["balances"][0]["amount"] == "100.00"
    assert out["statement"]["transactions"][0]["booking_date"] == "2025 - 01 - 02"
    assert out["statement"]["transactions"][0]["value_date"] == "2025 - 01 - 02"
